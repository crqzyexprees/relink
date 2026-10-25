"""Streamlit presentation only; extraction and recovery live in engine modules."""

from datetime import datetime
from dataclasses import asdict, replace
import hashlib
import logging
import os
from urllib.parse import quote

import streamlit as st

from relink.extraction import PDFExtractionError, extract_pdf_links
from relink.identifiers import normalize_doi
from relink.models import MatchStatus, SearchQuery
from relink.paper_models import Paper
from relink import gemini_config
from relink.gemini_ui import render_identification
from relink.papers import lookup_uploaded_datasets
from relink.history_access import (IdentityChanged, current_access, ensure_action_scope,
                                  rerun_if_identity_changed, sync_session_scope)
from relink.exports import json_download
from relink.history_ui import record_search, render_history
from relink.paper_ui import render_paper_workspace
from relink.workflow import public_link, query_from_input, report_json, run_recovery, paper_dataset_report
from relink.dataset_ui import render_options


from relink.theme import STYLE


SOURCE_NAMES = {'internet_archive': 'Internet Archive', 'datacite': 'DataCite', 'request_policy': 'Address safety check'}
ACCESS_NAMES = {'working': 'Original URL is working', 'not_found': 'Original URL returned 404',
                'forbidden': 'Original URL returned 403', 'rate_limited': 'Original URL is rate limited',
                'dns_failure': 'Original hostname could not be resolved', 'timeout': 'Original URL check timed out',
                'blocked': 'Unsafe URL access was blocked', 'redirect_error': 'Original URL has a redirect error',
                'http_error': 'Original URL returned an HTTP error', 'network_error': 'Original URL could not be reached'}


def _clear_report():
    st.session_state.pop('report', None)
    st.session_state.pop('recovery_error', None)
    st.session_state.pop('uploaded_dataset_lookup', None)


def _link(label, value, key_prefix='dataset'):
    safe = public_link(value)
    if safe:
        st.link_button(label, safe, key=key_prefix + ':' + label)
    elif value:
        st.caption('This address is not available as a public web link.')


def _pdf_input():
    upload = st.file_uploader('Research paper', type=['pdf'], key='paper_upload',
                              help='PDF only · up to 10 MB and 100 pages. No OCR.')
    if upload is None:
        st.session_state.pop('_pdf_fingerprint', None)
        st.session_state.pop('_pdf_extraction', None)
        return '', None, {'mode': 'pdf'}
    content = upload.getvalue()
    fingerprint = hashlib.sha256(content).hexdigest()
    if fingerprint != st.session_state.get('_pdf_fingerprint'):
        _clear_report()
        st.session_state.pop('pdf_link', None)
        st.session_state.pop('_selected_pdf_link', None)
        st.session_state.pop('_pdf_extraction', None)
        st.session_state['_pdf_fingerprint'] = fingerprint
        try:
            with st.spinner('Extracting links from the PDF…'):
                st.session_state['_pdf_extraction'] = extract_pdf_links(content)
            st.session_state.pop('_pdf_error', None)
        except PDFExtractionError as exc:
            st.session_state['_pdf_error'] = str(exc)
    if '_pdf_error' in st.session_state:
        st.error('The PDF could not be analyzed.')
        st.text(st.session_state['_pdf_error'])
        return '', None, {'mode': 'pdf'}
    extracted = st.session_state.get('_pdf_extraction')
    if extracted is None:
        return '', None, {'mode': 'pdf'}
    st.caption(f'{extracted.page_count} page(s) · {len(extracted.links)} HTTP(S) link(s) extracted')
    if extracted.title:
        st.text(extracted.title)
    for warning in extracted.warnings:
        st.warning(warning)
    if not extracted.links:
        st.info('No public HTTP or HTTPS links were found. Gemini can identify dataset names from readable text.')
        return '', extracted, {'mode': 'pdf', 'filename': upload.name, 'document_sha256': fingerprint,
                               'page_count': extracted.page_count}
    by_url = {link.url: link for link in extracted.links}

    def label(url):
        pages = ', '.join(str(page) for page in sorted({o.page for o in by_url[url].occurrences}))
        return f'{url} · page {pages}'

    selected = st.selectbox('Choose a research link', list(by_url), format_func=label, key='pdf_link')
    link = by_url[selected]
    if st.session_state.get('_selected_pdf_link') != selected:
        st.session_state['dataset_context'] = link.occurrences[0].context[:1000]
        st.session_state['_selected_pdf_link'] = selected
    st.caption('Surrounding text')
    st.text(link.occurrences[0].context or 'No nearby text was available for this embedded link.')
    context = {'mode': 'pdf', 'filename': upload.name, 'document_sha256': fingerprint,
               'page_count': extracted.page_count, 'selected_link': selected,
               'occurrences': [vars(occurrence) for occurrence in link.occurrences],
               'extraction_warnings': list(extracted.warnings)}
    return selected, extracted, context


def _render_access(current, original_url, key_prefix='dataset'):
    st.subheader('Original URL')
    label = ACCESS_NAMES.get(current.status, 'Original URL status is inconclusive')
    if current.status == 'working':
        st.success(label)
    elif current.status == 'blocked':
        st.error(label)
    else:
        st.warning(label)
    if current.http_status is not None:
        st.caption(f'HTTP {current.http_status}')
    st.text(original_url)
    _link('Open original source', original_url, key_prefix)
    if current.final_url != original_url:
        st.caption('Final checked address')
        st.text(current.final_url)
    if current.detail:
        st.text(current.detail)
    if current.retry_after:
        st.text('Retry-After: ' + current.retry_after)
    if current.redirects:
        with st.expander('Redirect history'):
            for url in current.redirects:
                st.text(url)


def _render_candidate(index, ranked, key_prefix='dataset'):
    candidate = ranked.candidate
    with st.container(border=True):
        heading, points = st.columns([4, 1])
        with heading:
            st.subheader('Best-ranked option' if index == 1 else f'Option {index}')
            st.text(candidate.titles[0] if candidate.titles else 'Archived resource' if candidate.archived_url else 'Repository record')
        with points:
            st.metric('Relevance points', ranked.score)
        if ranked.status == MatchStatus.VERIFIED_EXACT_MATCH:
            st.success('Verified exact match · independent identity evidence supplied')
        elif ranked.status == MatchStatus.LIKELY_MATCH:
            st.warning('Likely match · content is unverified')
        elif ranked.status == MatchStatus.DIFFERENT_VERSION:
            st.warning('Different version')
        else:
            st.info('Unverified candidate')
        location = candidate.url or candidate.archived_url
        if location:
            st.text(location)
            _link(f'Open candidate {index}', location, key_prefix)
        doi = normalize_doi(candidate.doi)
        if candidate.doi:
            st.text('DOI: ' + candidate.doi)
        if doi:
            _link(f'Open DOI record {index}', 'https://doi.org/' + quote(doi, safe='/'), key_prefix)
        st.text('Source: ' + SOURCE_NAMES.get(candidate.source, candidate.source))
        if candidate.capture_timestamp:
            try:
                timestamp = datetime.strptime(candidate.capture_timestamp, '%Y%m%d%H%M%S').strftime('%b %d, %Y · %H:%M:%S UTC')
            except ValueError:
                timestamp = candidate.capture_timestamp
            st.text('Archived: ' + timestamp)
        if candidate.year is not None:
            st.text(f'Published: {candidate.year}')
        if candidate.retrieved_at:
            st.text('Metadata retrieved: ' + candidate.retrieved_at)
        st.text('Source evidence: ' + candidate.verification_status.replace('_', ' '))
        st.text(candidate.limitation)
        signal_labels = {'url': 'Matching original URL', 'doi': 'Matching DOI',
                         'filename': 'Matching filename', 'title': 'Matching title words',
                         'author': 'Matching author words', 'institution': 'Matching institution words',
                         'description': 'Matching context words', 'year': 'Matching publication year',
                         'hash': 'Matching independent hash evidence'}
        support = [signal_labels.get(e.signal, e.signal) for e in ranked.explanation if e.points > 0]
        st.text('Why this option: ' + ('; '.join(dict.fromkeys(support)) if support else
                'No positive matching evidence was found; inspect this unverified lead carefully.'))
        if ranked.ai_reason:
            st.text('AI relevance (judgment): ' + ranked.ai_reason)
            st.text('Supporting ' + ranked.ai_field.lower() + ': ' + ranked.ai_evidence)
        with st.expander('Evidence and ranking', expanded=index == 1):
            for evidence in candidate.evidence:
                st.text(evidence)
            if ranked.explanation:
                st.dataframe([{'Signal': e.signal, 'Points': e.points, 'Reason': e.detail,
                               'Requested': ' · '.join(e.query_values), 'Observed': ' · '.join(e.candidate_values)}
                              for e in ranked.explanation], hide_index=True, width='stretch')
        with st.expander('Original source records'):
            for number, provenance in enumerate(candidate.provenance, 1):
                st.text(SOURCE_NAMES.get(provenance.source, provenance.source))
                if provenance.url:
                    st.text(provenance.url)
                    _link(f'Open source {index}.{number}', provenance.url, key_prefix)
                if provenance.doi:
                    st.text('Returned DOI: ' + provenance.doi)
                if provenance.metadata:
                    st.json(provenance.metadata, expanded=False)


def _render_report(report, key_prefix='dataset'):
    st.divider()
    st.subheader('Recovery report')
    st.caption('A ranked lead is not proof that the original dataset survives. Points describe relevance, not probability.')
    if report.query.original_url: _render_access(report.current, report.query.original_url, key_prefix)
    else: st.text('Dataset search: ' + (report.query.doi or report.query.title or report.query.description))
    render_identification(report.identification, report.named_searches, key_prefix=key_prefix + '_ai',
                          show_candidates=report.discovery.assessment is None)
    status = report.discovery.status
    if status == 'partial':
        st.warning('Some sources could not complete. Available candidates are shown below.')
    elif status == 'error':
        st.error('Recovery could not complete. Review the source errors below.')
    elif status == 'not_found':
        st.info('No candidates were reported for this search. This does not prove that no copy exists.')
    with st.expander('Source checks', expanded=status in ('partial', 'error')):
        for provider in report.discovery.providers:
            st.text(SOURCE_NAMES.get(provider.source, provider.source) + ' · ' + provider.status.replace('_', ' '))
            if provider.status not in ('found', 'not_found', 'not_applicable'):
                st.error('This source did not complete successfully.')
            st.text(provider.detail)
            if provider.retry_after:
                st.text('Retry-After: ' + provider.retry_after)
            if provider.truncated:
                st.warning('This source returned an incomplete or limited result set.')
            for warning in provider.warnings:
                st.text(warning)
    render_options(report.discovery, key_prefix=key_prefix, render_candidate=_render_candidate, snapshot_id=report.generated_at)
    try:
        exported = report_json(report)
    except (TypeError, ValueError):
        st.error('The report contains source data that could not be exported as valid JSON.')
    else:
        st.caption('Optional: save a machine-readable record of the input, source checks, ranked options, '
                   'evidence, and search time for sharing or auditing. The JSON report is not a dataset download; '
                   'all results can be read above without downloading it.')
        json_download('Download evidence report (.json)', data=exported,
                           file_name='relink-recovery-report.json', key=key_prefix + '_report_download',
                           help='JSON preserves the structured search evidence for another person or program to inspect.')
    st.caption('Report generated ' + report.generated_at)


def _render_license():
    st.subheader('License & source')
    st.caption('Open source · AGPL-3.0-only')
    with st.container(border=True):
        st.text('Copyright (C) 2026 ReLink contributors. ReLink is free software: '
                'you may redistribute and modify it under GNU AGPL version 3. '
                'It is provided WITHOUT ANY WARRANTY, including merchantability '
                'or fitness for a particular purpose.')
        st.link_button('Read the AGPLv3 license', 'https://www.gnu.org/licenses/agpl-3.0.html')
        source_url = public_link(os.environ.get('RELINK_SOURCE_URL', '').strip())
        if source_url:
            st.link_button('Source code', source_url)
        else:
            st.warning('Source code link is not configured for this deployment. '
                       'The operator must provide the corresponding release source.')


def main():
    st.set_page_config(page_title='ReLink · Research dataset recovery', page_icon='🔗', layout='wide')
    sync_session_scope(current_access())
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.container(key='relink_navigation'):
        with st.container(key='relink_brand'):
            st.title('ReLink', anchor=False)
            st.caption('A research workspace')
        datasets, papers, license_tab = st.tabs(['Find datasets', 'Find papers', 'License & source'])
        with datasets:
            _render_dataset_workspace()
        with papers:
            render_paper_workspace(lambda report: _render_report(report,
                key_prefix='paper_combined' if report.input_context.get('mode') == 'paper_datasets' else 'paper'))
        with license_tab:
            _render_license()
    render_history(_render_report)


def _dataset_example(mode, value):
    st.session_state['input_mode'] = mode
    st.session_state['dataset_topic' if mode == 'Search datasets' else 'original_url'] = value
    _clear_report()
    st.toast('Example ready. Click Find to search.')


def _render_dataset_workspace():
    st.subheader('Find datasets')
    st.caption('Recover a missing link, inspect a paper, or describe the data you need.')
    inputs, overview = st.columns([2.2, 1], gap='large')
    with inputs, st.container(border=True, key='dataset_input_panel'):
        mode = st.radio('Input mode', ['Recover URL', 'Analyze PDF', 'Search datasets'], horizontal=True, key='input_mode')
        if st.session_state.get('_mode') != mode:
            _clear_report()
            st.session_state['_mode'] = mode
            st.session_state['dataset_context'] = ''
            st.session_state.pop('_selected_pdf_link', None)
        if mode == 'Recover URL':
            url = st.text_input('Missing dataset URL', placeholder='https://research.example.org/dataset.zip',
                                key='original_url', help='Public HTTP or HTTPS addresses only.').strip()
            source_context = {'mode': 'url'}
            context = ''
            extracted = None
        elif mode == 'Analyze PDF':
            url, extracted, source_context = _pdf_input()
            with st.expander('Paper context (automatically extracted; optional to edit)'):
                context = st.text_area('Paper context', key='dataset_context', max_chars=1000,
                                       help='The selected URL and paper context are sent to recovery services when you click Find.')
        else:
            context = st.text_input('Dataset name, topic or DOI', key='dataset_topic',
                                    placeholder='e.g. penguin body mass and bill measurements', max_chars=1200).strip()
            url, extracted, source_context = '', None, {'mode': 'dataset_search'}
        if mode != 'Analyze PDF':
            st.caption('Quick start · fill an example, then click Find')
            examples = st.columns(2)
            examples[0].button('Iris DOI', key='dataset_example_iris', on_click=_dataset_example,
                               args=('Search datasets', '10.24432/c56c76'), width='stretch')
            if mode == 'Recover URL':
                examples[1].button('Missing MNIST link', key='dataset_example_mnist', on_click=_dataset_example,
                    args=('Recover URL', 'http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz'), width='stretch')
        signature = (mode, url, context, source_context.get('document_sha256'), source_context.get('filename'))
        if signature != st.session_state.get('_input_signature'):
            _clear_report()
            st.session_state['_input_signature'] = signature
        settings = gemini_config.load_gemini_settings()
        can_identify = bool(extracted and extracted.has_text and settings.api_key)
        if extracted and extracted.has_text and not url and not settings.api_key:
            st.info('Gemini access must be configured to identify dataset names in a PDF without web links.')
        recover = st.button('Find', type='primary', disabled=not bool(url or can_identify or (mode == 'Search datasets' and context)), width='stretch')
        if mode == 'Analyze PDF':
            st.caption('On Find, Gemini identifies dataset names from text excerpts and DataCite searches those names. '
                       'Excerpts are sent to Google; use public, nonconfidential papers. PDF files stay in this session.')
        else:
            st.caption('Paste a link and click Find; no description is required.' if mode == 'Recover URL' else
                       'Describe the data you need, or enter its DOI. Find searches real dataset records.')
        st.caption('Find sends your query, public metadata, and any bounded CSV/TSV header plus up to three rows '
                   'to Google for relevance ranking. At most three files are sampled, 64 KiB each; use nonconfidential data. '
                   'Metadata and samples do not verify the original dataset. Load more makes no new requests.')
    with overview, st.container(key='evidence_panel'):
        st.subheader('Mission briefing')
        st.markdown('**Internet Archive**')
        st.caption('Look for reported captures of the original address.')
        st.markdown('**DataCite**')
        st.caption('Discover dataset records, repository locations, and DOIs.')
        st.markdown('**Gemini + source evidence**')
        st.caption('Compare metadata and tiny table samples. Exact identity and version evidence stay authoritative.')
        st.markdown('**Inspect before you trust**')
        st.caption('Compare source records, ranking signals, and verification limits.')
    if recover:
        action_scope = current_access().scope
        _clear_report()
        with st.status('Searching for dataset signals', expanded=True) as activity:
            try:
                if mode == 'Search datasets':
                    doi = normalize_doi(context)
                    query = SearchQuery(doi=doi) if doi else SearchQuery(description=' '.join(context.split()))
                    report = run_recovery(query, input_context=source_context, on_progress=activity.write, settings=settings)
                elif url:
                    query = query_from_input(url, context)
                    report = run_recovery(query, input_context=source_context, on_progress=activity.write,
                                          settings=settings if mode == 'Recover URL' else None)
                else:
                    report = None
                lookup = None
                if mode == 'Analyze PDF' and extracted is not None:
                    activity.write('Gemini is identifying dataset mentions; DataCite will search supported names')
                    lookup = lookup_uploaded_datasets(extracted, paper_id='uploaded-pdf:' + source_context['document_sha256'],
                                                     settings=settings, initial=report.discovery if report else None)
                    if report is not None:
                        report = replace(report, identification=lookup.identification, named_searches=lookup.named_searches,
                                         discovery=lookup.combined or report.discovery)
                ensure_action_scope(action_scope)
            except IdentityChanged:
                st.rerun()
            except ValueError as exc:
                activity.update(label='Recovery request rejected', state='error')
                st.session_state['recovery_error'] = ('Enter a valid public HTTP or HTTPS URL.', str(exc))
            except Exception:
                logging.getLogger(__name__).exception('Recovery workflow failed')
                activity.update(label='Recovery could not complete', state='error')
                st.session_state['recovery_error'] = (
                    'An unexpected error interrupted recovery. Try again or inspect the app logs.', '')
            else:
                if report is not None:
                    st.session_state['report'] = report
                    failed = report.discovery.status in ('error', 'partial')
                else:
                    st.session_state['uploaded_dataset_lookup'] = lookup
                    failed = lookup.identification.status not in ('found', 'not_found')
                activity.update(label='Search finished with source issues' if failed else 'Search finished',
                                state='error' if failed else 'complete', expanded=failed)
                if report is not None:
                    record_search('recovery', query.original_url or query.doi or query.description, report, expected_scope=action_scope)
                else:
                    paper = Paper(lookup.paper_id, extracted.title or source_context['filename'])
                    record_search('paper_datasets', paper.title, lookup, request={'paper': asdict(paper)}, expected_scope=action_scope)
            finally:
                rerun_if_identity_changed(action_scope)
    error = st.session_state.get('recovery_error')
    if error:
        st.error(error[0])
        if error[1]: st.text(error[1])
    report = st.session_state.get('report')
    if report is not None:
        _render_report(report)
    lookup = st.session_state.get('uploaded_dataset_lookup')
    if lookup is not None:
        render_identification(lookup.identification, lookup.named_searches, key_prefix='upload_ai', show_candidates=lookup.combined is None)
        if lookup.combined is not None:
            _render_report(paper_dataset_report(lookup, 'uploaded research paper'), key_prefix='upload_combined')
