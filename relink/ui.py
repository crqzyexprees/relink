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
from relink.models import MatchStatus
from relink.paper_models import Paper
from relink import gemini_config
from relink.gemini_ui import render_identification
from relink.papers import lookup_uploaded_datasets
from relink.history_access import (IdentityChanged, current_access, ensure_action_scope,
                                  rerun_if_identity_changed, sync_session_scope)
from relink.exports import json_download
from relink.history_ui import record_search, render_history
from relink.paper_ui import render_paper_workspace
from relink.workflow import public_link, query_from_input, report_json, run_recovery


# This constant contains only application-owned CSS. Untrusted values are always
# rendered with st.text, native table cells, or st.json; never interpolated here.
STYLE = '''
<style>
.stApp {
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: #0e161d;
    background-image:
        radial-gradient(ellipse at 8% 0%, rgba(45, 212, 191, .10) 0%,
            rgba(45, 212, 191, .065) 25%, rgba(45, 212, 191, .025) 52%, rgba(45, 212, 191, 0) 82%),
        radial-gradient(ellipse at 95% 40%, rgba(77, 126, 196, .065) 0%,
            rgba(77, 126, 196, .025) 40%, rgba(77, 126, 196, 0) 85%),
        linear-gradient(rgba(148, 163, 184, .014) 1px, transparent 1px),
        linear-gradient(90deg, rgba(148, 163, 184, .014) 1px, transparent 1px);
    background-size: auto, auto, 64px 64px, 64px 64px;
    background-attachment: fixed;
}
[data-testid="stHeader"] { background: transparent; }
.block-container { max-width: 1280px; padding-top: 5rem; padding-bottom: 4rem; }
h1 { letter-spacing: -.055em; font-size: 3.7rem !important; font-weight: 750 !important; color: inherit; }
h2, h3 { letter-spacing: -.025em; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 14px; background: var(--secondary-background-color); border-color: rgba(148, 163, 184, .24); }
.st-key-relink_hero {
    padding: 1.8rem 2rem;
    border: 1px solid rgba(45, 212, 191, .12);
    border-radius: 18px;
    background: linear-gradient(110deg, rgba(45, 212, 191, .075) 0%,
        rgba(45, 212, 191, .045) 30%, rgba(45, 212, 191, .015) 65%, rgba(45, 212, 191, 0) 100%);
    box-shadow: 0 12px 50px rgba(0, 0, 0, .07);
    gap: .5rem;
}
.st-key-relink_hero h1 { color: #e6faf6; padding-top: 0; }
.st-key-relink_hero h3 { font-size: 1.6rem; padding-top: 0; }
.st-key-dataset_input_panel, .st-key-evidence_panel {
    border-radius: 16px;
    border: 1px solid rgba(148, 163, 184, .18);
    background: linear-gradient(145deg, rgba(21, 35, 45, .8), rgba(17, 28, 37, .65));
    box-shadow: 0 12px 32px rgba(0, 0, 0, .14);
    padding: 1.5rem;
}
.st-key-evidence_panel { border-top: 2px solid rgba(45, 212, 191, .55); }
.st-key-evidence_panel strong { color: #8ce4d7; }
[data-baseweb="tab-list"] { gap: 1.5rem; }
[data-baseweb="tab"] { padding: .75rem .35rem; }
.stButton button[kind="primary"] { box-shadow: 0 4px 18px rgba(45, 212, 191, .13); }
[data-testid="stText"] { font-family: inherit; white-space: pre-wrap; overflow-wrap: anywhere; line-height: 1.6; }
[data-testid="stMetricValue"] { font-size: 1.65rem; }
[data-testid="stFileUploader"] { border-radius: 12px; }
.stButton button, .stDownloadButton button, .stLinkButton a { border-radius: 8px; }
@media(max-width: 640px) {
    .block-container { padding: 4.5rem 1rem 3rem; }
    .st-key-relink_hero { padding: 1.25rem; }
    .st-key-dataset_input_panel, .st-key-evidence_panel { padding: 1rem; }
    h1 { font-size: 2.8rem !important; }
}
</style>
'''

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
    _render_access(report.current, report.query.original_url, key_prefix)
    render_identification(report.identification, report.named_searches, key_prefix=key_prefix + '_ai')
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
    if report.discovery.candidates:
        st.subheader('Best-ranked options')
        st.caption(f'{len(report.discovery.candidates)} candidate(s), sorted by matching evidence across the returned results. '
                   'The highest relevance score appears first; equal scores are ties, not stronger recommendations.')
        if len(report.discovery.candidates) == 1:
            st.caption('Only one candidate was returned by the sources. This is the only available lead, '
                       'not a comparison winner. Archive availability supplies at most one closest capture.')
    for index, candidate in enumerate(report.discovery.candidates, 1):
        _render_candidate(index, candidate, key_prefix)
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


def main():
    st.set_page_config(page_title='ReLink · Research dataset recovery', page_icon='🔗', layout='wide')
    sync_session_scope(current_access())
    st.markdown(STYLE, unsafe_allow_html=True)
    with st.container(key='relink_hero'):
        st.caption('RESEARCH WORKSPACE')
        st.title('ReLink')
        st.markdown('### Reconnect your research.')
        st.caption('Find relevant papers. Trace missing datasets. Follow evidence you can inspect.')
    st.caption('Open source · AGPL-3.0-only')
    with st.expander('License and source code'):
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
    datasets, papers = st.tabs(['Find datasets', 'Find papers'])
    with datasets:
        _render_dataset_workspace()
    with papers:
        render_paper_workspace(lambda report: _render_report(report, key_prefix='paper'))
    render_history(_render_report)


def _render_dataset_workspace():
    inputs, overview = st.columns([2.2, 1], gap='large')
    with inputs, st.container(border=True, key='dataset_input_panel'):
        mode = st.radio('Input mode', ['Recover URL', 'Analyze PDF'], horizontal=True, key='input_mode')
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
        else:
            url, extracted, source_context = _pdf_input()
            with st.expander('Paper context (automatically extracted; optional to edit)'):
                context = st.text_area('Paper context', key='dataset_context', max_chars=1000,
                                       help='The selected URL and paper context are sent to recovery services when you click Find.')
        signature = (mode, url, context, source_context.get('document_sha256'), source_context.get('filename'))
        if signature != st.session_state.get('_input_signature'):
            _clear_report()
            st.session_state['_input_signature'] = signature
        settings = gemini_config.load_gemini_settings() if mode == 'Analyze PDF' else gemini_config.GeminiSettings()
        can_identify = bool(extracted and extracted.has_text and settings.api_key)
        if extracted and extracted.has_text and not url and not settings.api_key:
            st.info('Gemini access must be configured to identify dataset names in a PDF without web links.')
        recover = st.button('Find', type='primary', disabled=not bool(url or can_identify), width='stretch')
        if mode == 'Analyze PDF':
            st.caption('On Find, Gemini identifies dataset names from text excerpts and DataCite searches those names. '
                       'Excerpts are sent to Google; use public, nonconfidential papers. PDF files stay in this session.')
        else:
            st.caption('Paste a link and click Find. No description is required. The URL goes to the recovery providers.')
    with overview, st.container(key='evidence_panel'):
        st.subheader('Follow the evidence')
        st.markdown('**Internet Archive**')
        st.caption('Look for reported captures of the original address.')
        st.markdown('**DataCite**')
        st.caption('Discover dataset records, repository locations, and DOIs.')
        st.markdown('**Inspect before you trust**')
        st.caption('Compare source records, ranking signals, and verification limits.')
    if recover:
        action_scope = current_access().scope
        _clear_report()
        with st.status('Finding matches for the selected URL', expanded=True) as activity:
            try:
                if url:
                    query = query_from_input(url, context)
                    report = run_recovery(query, input_context=source_context, on_progress=activity.write)
                else:
                    report = None
                lookup = None
                if mode == 'Analyze PDF' and extracted is not None:
                    activity.write('Gemini is identifying dataset mentions; DataCite will search supported names')
                    lookup = lookup_uploaded_datasets(extracted, paper_id='uploaded-pdf:' + source_context['document_sha256'],
                                                     settings=settings)
                    if report is not None:
                        report = replace(report, identification=lookup.identification, named_searches=lookup.named_searches)
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
                    record_search('recovery', query.original_url, report, expected_scope=action_scope)
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
        render_identification(lookup.identification, lookup.named_searches, key_prefix='upload_ai')
