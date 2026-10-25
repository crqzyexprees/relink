"""Thin Streamlit paper discovery and dataset handoff, without provider logic."""
from dataclasses import asdict
import logging

import streamlit as st

from relink.papers import lookup_paper_datasets, search_papers
from relink.history_ui import record_search
from relink import gemini_config
from relink.gemini_ui import render_identification
from relink.history_access import IdentityChanged, current_access, ensure_action_scope, rerun_if_identity_changed
from relink.workflow import public_link, query_from_input, run_recovery, paper_dataset_report
from relink.dataset_ui import SAMPLE_DISCLOSURE


def _clear(*keys):
    for key in keys: st.session_state.pop(key, None)


def _source(label, url, key):
    safe = public_link(url)
    if safe: st.link_button(label, safe, key=key)


def _show_action_error(key, title):
    detail = st.session_state.get(key)
    if detail:
        st.error(title)
        st.text(detail)


def _search_topic(topic, state_keys, *, batch=0, exclude_identifiers=()):
    action_scope = current_access().scope
    _clear(*state_keys)
    try:
        with st.spinner('Searching OpenAlex and arXiv, then ranking available abstracts with Gemini…'):
            found = search_papers(topic, settings=gemini_config.load_gemini_settings(), batch=batch,
                                  exclude_identifiers=exclude_identifiers)
        ensure_action_scope(action_scope)
        st.session_state['paper_search_result'] = found
        st.session_state['paper_visible_count'] = 10
        record_search('papers', topic, found, request={'topic': topic}, expected_scope=action_scope)
    except IdentityChanged:
        st.rerun()
    except ValueError as exc:
        st.session_state['paper_search_error'] = str(exc)
    except Exception:
        logging.getLogger(__name__).exception('Paper search failed')
        st.session_state['paper_search_error'] = 'Try again or inspect the app logs.'
    finally:
        rerun_if_identity_changed(action_scope)


def render_paper_workspace(render_report):
    st.subheader('Find papers by topic')
    st.caption('Describe your research interest. Find up to 30 papers and rank their abstracts with Gemini.')
    with st.expander('How matching works'):
        st.text('OpenAlex and arXiv each return up to 15 records per batch using up to 12 topic keywords. '
                'Duplicates are merged with source evidence retained. Gemini orders the supplied abstract excerpts '
                'against your description and selects a numbered supporting passage from each abstract. '
                'Evidence text comes from the supplied source passage; Gemini does not write quotations. '
                'Reasons are AI judgments, not verified facts. If Gemini is unavailable, whole-word abstract matches '
                'determine order (10 points per keyword; equal points are ties). Missing abstracts cannot be ranked. '
                'Load more reveals cached results; Search more fetches a separately ranked next batch, up to three batches. '
                'Relevance is not paper quality, verification or a probability.')
    topic = st.text_area('Topic or research description', key='paper_topic', max_chars=1200,
                         placeholder='For example: question answering datasets for reading comprehension')
    state_keys = ('paper_search_result', 'paper_choice', 'paper_lookup_result',
                  'paper_link_report', 'paper_dataset_link', '_selected_paper', '_selected_paper_link',
                  'paper_search_error', 'paper_lookup_error', 'paper_link_error', 'paper_visible_count')
    if topic != st.session_state.get('_paper_topic_signature'):
        _clear(*state_keys)
        st.session_state['_paper_topic_signature'] = topic
    st.caption('Find papers sends your topic to the paper sources and your topic plus public abstract excerpts '
               'to Google for ranking. Use nonconfidential descriptions. Load more makes no new requests.')
    if st.button('Find papers', key='find_papers', disabled=not bool(topic.strip()), type='primary'):
        _search_topic(topic, state_keys)
    _show_action_error('paper_search_error', 'Paper search could not complete.')
    result = st.session_state.get('paper_search_result')
    if result is None: return
    st.text(result.detail)
    if result.status not in ('found', 'not_found', 'partial'):
        st.error('The paper sources could not complete the search.')
        if result.retry_after: st.text('Retry-After: ' + result.retry_after)
        for provider in result.providers: st.text(provider.source + ': ' + provider.status + ' · ' + provider.detail)
        return
    if result.status == 'partial': st.warning('Some paper sources did not complete; available results are shown.')
    for warning in result.warnings: st.text(warning)
    if result.ranking:
        if result.ranking.status == 'ranked': st.caption('Ranking: Gemini abstract relevance · ' + result.ranking.model)
        elif result.ranking.status != 'no_abstracts': st.warning('Keyword fallback · Gemini ranking: ' + result.ranking.status.replace('_', ' '))
        st.text(result.ranking.detail)
        if result.ranking.retry_after: st.text('Gemini Retry-After: ' + result.ranking.retry_after)
    if result.providers:
        with st.expander('Paper source checks'):
            for index, provider in enumerate(result.providers):
                st.text(f'{provider.source}: {provider.status.replace("_", " ")} · {provider.count} records. {provider.detail}')
                if provider.retry_after: st.text('Retry-After: ' + provider.retry_after)
                _source('Open source query', provider.query_url, f'paper_source_query_{index}')
    visible_count = st.session_state.get('paper_visible_count', 10)
    if visible_count < len(result.papers) and st.button('Load more · next 10', key='paper_load_more'):
        visible_count = min(visible_count + 10, len(result.papers))
        st.session_state['paper_visible_count'] = visible_count
        st.rerun()
    if visible_count >= len(result.papers) and result.has_more:
        st.caption('All ranked papers in this batch are visible. Search more queries the next source pages '
                   'and ranks unseen abstracts as a new batch; previous ranks are not compared across batches.')
        if st.button('Search more · new batch', key='paper_search_more'):
            _search_topic(topic, state_keys, batch=result.batch + 1, exclude_identifiers=result.seen_identifiers)
            st.rerun()
    st.caption(f'Batch {result.batch + 1} · Showing {min(visible_count, len(result.papers))} of {len(result.papers)} ranked papers. '
               f'{result.retrieved_count} unique records retrieved; {result.missing_abstracts} had no abstract. '
               'Ranks apply to this batch only.')
    if not result.papers:
        st.info('No unseen abstract matches are available in this batch. Try a few specific topic words or another batch when available.')
        return
    visible = result.papers[:visible_count]
    st.dataframe([{'Rank': index, 'Paper': item.paper.title, 'Year': item.paper.year,
                   'Keyword points': item.score, 'Matched keywords': ', '.join(item.matched_terms),
                   'AI relevance reason': item.semantic_reason}
                  for index, item in enumerate(visible, 1)], hide_index=True, width='stretch')
    by_id = {item.paper.id: item for item in visible}
    selected = st.selectbox('Choose a paper to inspect and find its datasets', list(by_id),
                            format_func=lambda identifier: by_id[identifier].paper.title, key='paper_choice')
    if selected != st.session_state.get('_selected_paper'):
        _clear('paper_lookup_result', 'paper_link_report', 'paper_dataset_link', '_selected_paper_link',
               'paper_lookup_error', 'paper_link_error')
        st.session_state['_selected_paper'] = selected
    ranked = by_id[selected]
    paper = ranked.paper
    st.text(paper.title)
    st.caption('Authors: ' + (', '.join(paper.authors) or 'Not supplied') +
               ' · Year: ' + (str(paper.year) if paper.year else 'Not supplied'))
    st.text('Matched abstract keywords: ' + ', '.join(ranked.matched_terms))
    st.caption(f'{len(ranked.matched_terms)} of {len(ranked.query_terms)} selected keywords matched · {ranked.score} relevance points')
    if ranked.semantic_rank is not None:
        st.text('AI relevance reason (judgment): ' + ranked.semantic_reason)
        st.text('Supporting abstract passage (from source): ' + ranked.semantic_evidence)
    if len(paper.abstract) > 1200:
        st.text(paper.abstract[:1200].rstrip() + '…')
        with st.expander('Read full abstract'):
            st.text(paper.abstract)
    else:
        st.text(paper.abstract)
    _source('Open paper record', paper.id, 'open_paper_record')
    _source('Open publisher or repository', paper.landing_url, 'open_paper_landing')
    if paper.doi: _source('Open paper DOI', 'https://doi.org/' + paper.doi, 'open_paper_doi')
    _source('Open advertised PDF', paper.pdf_url, 'open_paper_pdf')
    st.caption('Source: ' + ', '.join(dict.fromkeys(p.source for p in paper.provenance) or (paper.source,)) +
               ' · Retrieved: ' + (paper.retrieved_at or 'Not supplied'))
    if len(paper.provenance) > 1:
        for index, origin in enumerate(paper.provenance):
            _source('Open ' + origin.source + ' record', origin.record_url, f'paper_provenance_{index}')
    st.caption('Find datasets searches records related to this paper DOI and, when advertised, downloads one public PDF '
               'to extract research links. Gemini also identifies dataset names from text excerpts and searches DataCite. '
               'This sends excerpts to Google; use public, nonconfidential papers. Quotes are checked locally.')
    st.caption(SAMPLE_DISCLOSURE)
    if st.button('Find datasets from this paper', key='lookup_paper_datasets'):
        action_scope = current_access().scope
        _clear('paper_lookup_result', 'paper_link_report', 'paper_dataset_link', '_selected_paper_link',
               'paper_lookup_error', 'paper_link_error')
        try:
            with st.spinner('Checking related dataset metadata and available paper links…'):
                found = lookup_paper_datasets(
                    paper, settings=gemini_config.load_gemini_settings())
            ensure_action_scope(action_scope)
            st.session_state['paper_lookup_result'] = found
            record_search('paper_datasets', paper.title, found,
                          request={'paper': asdict(paper)}, expected_scope=action_scope)
        except IdentityChanged:
            st.rerun()
        except Exception:
            logging.getLogger(__name__).exception('Paper dataset lookup failed')
            st.session_state['paper_lookup_error'] = 'Try again or inspect the app logs. No substitute results were generated.'
        finally:
            rerun_if_identity_changed(action_scope)
    _show_action_error('paper_lookup_error', 'Dataset lookup was interrupted.')
    lookup = st.session_state.get('paper_lookup_result')
    if lookup is None: return
    render_identification(lookup.identification, lookup.named_searches, key_prefix='paper_ai', show_candidates=lookup.combined is None)
    if lookup.combined is not None: render_report(paper_dataset_report(lookup, paper.title))
    st.subheader('Dataset evidence from the selected paper')
    st.text('Paper PDF: ' + lookup.pdf_status.replace('_', ' ') + ' · ' + lookup.detail)
    datasets = lookup.datasets
    st.text('Related dataset metadata: ' + datasets.status.replace('_', ' ') + ' · ' + datasets.detail)
    if datasets.retry_after: st.text('Retry-After: ' + datasets.retry_after)
    if datasets.status not in ('found', 'not_found', 'not_applicable'):
        st.warning('Related dataset lookup did not complete fully; inspect any available evidence below.')
    for warning in datasets.warnings: st.text(warning)
    if datasets.truncated: st.caption('The related-record search was limited; more records may exist.')
    for index, candidate in enumerate(datasets.candidates if lookup.combined is None else (), 1):
        with st.container(border=True):
            st.text(candidate.titles[0] if candidate.titles else 'Repository dataset record')
            st.caption('Source: DataCite · Unverified candidate. A metadata association is not proof '
                       'that this dataset was used in the paper or that its bytes are available.')
            if candidate.doi:
                st.text('DOI: ' + candidate.doi)
                _source('Open dataset DOI', 'https://doi.org/' + candidate.doi, f'paper_dataset_doi_{index}')
            if candidate.url:
                st.text(candidate.url)
                _source('Open repository record', candidate.url, f'paper_dataset_url_{index}')
            with st.expander('Dataset source evidence'):
                for provenance in candidate.provenance: st.json(provenance.metadata, expanded=False)
    if not lookup.links:
        st.info('No selectable research links were extracted. This does not prove the paper has no datasets.')
        return
    by_url = {link.url: link for link in lookup.links}
    selected_link = st.selectbox('Research link to check for dataset copies', list(by_url), key='paper_dataset_link')
    if selected_link != st.session_state.get('_selected_paper_link'):
        _clear('paper_link_report', 'paper_link_error')
        st.session_state['_selected_paper_link'] = selected_link
    link = by_url[selected_link]
    if link.occurrences:
        st.text('Link context: ' + link.occurrences[0].context)
    st.caption(SAMPLE_DISCLOSURE)
    if st.button('Find copies of selected link', key='recover_paper_link'):
        action_scope = current_access().scope
        _clear('paper_link_report', 'paper_link_error')
        try:
            with st.status('Checking the selected research link', expanded=True) as activity:
                found = run_recovery(query_from_input(selected_link),
                    input_context={'mode': 'paper', 'paper_id': paper.id, 'paper_doi': paper.doi,
                                   'selected_link': selected_link}, on_progress=activity.write,
                                   settings=gemini_config.load_gemini_settings())
                ensure_action_scope(action_scope)
                st.session_state['paper_link_report'] = found
                failed = st.session_state['paper_link_report'].discovery.status in ('partial', 'error')
                activity.update(label='Search finished with source issues' if failed else 'Search finished',
                                state='error' if failed else 'complete')
            record_search('recovery', selected_link, found, expected_scope=action_scope)
        except IdentityChanged:
            st.rerun()
        except ValueError as exc:
            st.session_state['paper_link_error'] = str(exc)
        except Exception:
            logging.getLogger(__name__).exception('Paper link recovery failed')
            st.session_state['paper_link_error'] = 'Try again or inspect the app logs. No substitute results were generated.'
        finally:
            rerun_if_identity_changed(action_scope)
    _show_action_error('paper_link_error', 'Link recovery could not complete.')
    report = st.session_state.get('paper_link_report')
    if report is not None: render_report(report)
