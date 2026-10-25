"""Local history presentation; all new network work requires Search again."""
from dataclasses import asdict
from datetime import datetime, timezone
import json
import logging

import streamlit as st

from relink.history import HistoryError, restore_paper, restore_snapshot
from relink.history_access import (authorized_store, current_access, ensure_action_scope,
                                  login_configured, rerun_if_identity_changed, store_for_access)
from relink.exports import json_download
from relink.paper_models import PaperDatasetLookup, PaperSearchResult
from relink.papers import lookup_paper_datasets, search_papers
from relink.workflow import RecoveryReport, public_link, run_recovery, paper_dataset_report
from relink import gemini_config
from relink.dataset_ui import SAMPLE_DISCLOSURE


def record_search(kind, label, result, *, expected_scope, request=None):
    ensure_action_scope(expected_scope)
    access = current_access()
    if not access.enabled: return None
    try:
        return authorized_store(expected_scope).add(kind, label[:2000], result, request=request)
    except (HistoryError, OSError):
        logging.getLogger(__name__).exception('Search history write failed')
        st.warning('Results are available, but history could not be saved. Check local storage permissions and limits.')
        return None


def _saved_link(label, value, key):
    safe = public_link(value)
    if safe: st.link_button(label, safe, key=key)


@st.dialog('Search results', width='large')
def _view(entry, render_report, *, expected_scope, saved=True, live_result=None):
    # Dialogs can rerun independently of main(): authorize before any content.
    try:
        store = authorized_store(expected_scope)
        if saved:
            entry = _owned_entry(store, entry.id)
    except HistoryError:
        # A fragment denial must clear the previous account's main page too.
        rerun_if_identity_changed(expected_scope)
        st.error('This saved result is unavailable for the current signed-in account.')
        return
    snapshot = restore_snapshot(entry) if live_result is None else live_result
    if saved:
        st.warning('Saved results · recorded ' + entry.created_at + '. This is a historical snapshot, not a fresh search.')
    else:
        st.warning('New results · not saved to history. Completed ' + datetime.now(timezone.utc).isoformat() + '.')
    st.text(entry.label)
    if isinstance(snapshot, RecoveryReport):
        render_report(snapshot, key_prefix='history')
    elif isinstance(snapshot, PaperSearchResult):
        st.text('Paper search: ' + snapshot.status.replace('_', ' '))
        st.text(snapshot.detail)
        if snapshot.ranking:
            st.text('Recorded Gemini ranking: ' + snapshot.ranking.status.replace('_', ' ') + ' · ' + snapshot.ranking.detail)
        if snapshot.retry_after: st.text('Retry-After recorded: ' + snapshot.retry_after)
        for index, ranked in enumerate(snapshot.papers, 1):
            with st.expander(f'Paper {index} · {ranked.score} recorded keyword points', expanded=index == 1):
                st.text(ranked.paper.title)
                st.text('Matched keywords: ' + ', '.join(ranked.matched_terms))
                if ranked.semantic_rank is not None:
                    st.text('Recorded AI relevance reason: ' + ranked.semantic_reason)
                    st.text('Recorded checked abstract quote: ' + ranked.semantic_evidence)
                st.text(ranked.paper.abstract)
                _saved_link('Open original paper record', ranked.paper.id, f'history_paper_{index}')
    elif isinstance(snapshot, PaperDatasetLookup):
        if snapshot.combined is not None:
            render_report(paper_dataset_report(snapshot, entry.label), key_prefix='history_combined')
        from relink.gemini_ui import render_identification
        render_identification(snapshot.identification, snapshot.named_searches, key_prefix='history_ai')
        st.text('Paper PDF: ' + snapshot.pdf_status.replace('_', ' ') + ' · ' + snapshot.detail)
        st.text('Related dataset search: ' + snapshot.datasets.status.replace('_', ' '))
        st.text(snapshot.datasets.detail)
        for index, candidate in enumerate(snapshot.datasets.candidates, 1):
            st.text(candidate.titles[0] if candidate.titles else 'Repository dataset record')
            st.caption('Recorded metadata candidate; dataset bytes remain unverified.')
            if candidate.doi:
                st.text(candidate.doi)
                _saved_link('Open saved DOI', 'https://doi.org/' + candidate.doi, f'history_doi_{index}')
            _saved_link('Open saved repository location', candidate.url, f'history_dataset_{index}')
        for index, link in enumerate(snapshot.links, 1):
            st.text(link.url)
            if link.occurrences: st.text(link.occurrences[0].context)
            _saved_link('Open recorded research link', link.url, f'history_research_link_{index}')
    with st.expander('Recorded evidence and request'):
        st.json({'request': entry.request, 'snapshot': asdict(snapshot)}, expanded=False)


def _owned_entry(store, entry_id):
    entry = next((entry for entry in store.list() if entry.id == entry_id), None)
    if entry is None: raise HistoryError('This search is unavailable in your history.')
    return entry


def _search_again(entry_id, expected_scope):
    entry = _owned_entry(authorized_store(expected_scope), entry_id)
    snapshot = restore_snapshot(entry)
    if entry.kind == 'recovery':
        result = run_recovery(snapshot.query, input_context=snapshot.input_context, settings=gemini_config.load_gemini_settings())
    elif entry.kind == 'papers':
        result = search_papers(entry.request['topic'], settings=gemini_config.load_gemini_settings())
    else:
        result = lookup_paper_datasets(restore_paper(entry), settings=gemini_config.load_gemini_settings())
    # Identity/expiry may have changed during the remote lookup. Do not expose
    # the old account's result or save it into a newly selected account.
    store = authorized_store(expected_scope)
    try:
        return store.add(entry.kind, entry.label, result, request=entry.request), True, None
    except (HistoryError, OSError):
        logging.getLogger(__name__).exception('Rerun completed but history could not be saved')
        # Keep the completed result independent of disk schema/size validation.
        return entry, False, result


def render_history(render_report):
    with st.sidebar:
        st.header('Search history')
        access = current_access()
        if access.mode == 'oidc':
            logged_in = st.user.to_dict().get('is_logged_in') is True
            if logged_in:
                if st.button('Sign out', key='history_logout'):
                    st.session_state.clear()
                    try:
                        st.logout()
                    except Exception:
                        st.error('Sign-out could not complete. Close this tab and check the authentication configuration.')
                    st.stop()
            elif login_configured():
                if st.button('Sign in for private history', key='history_login'):
                    st.session_state.clear()
                    try:
                        st.login()
                    except Exception:
                        st.error('Sign-in could not start. Ask the operator to check the authentication configuration.')
                    st.stop()
            else:
                st.caption('Private history sign-in is not configured for this deployment. Searches remain available.')
        if not access.enabled:
            st.caption(access.detail)
            return
        st.caption(access.detail + ' PDF files are not saved.')
        store = store_for_access(access)
        try:
            entries = store.list()
        except (HistoryError, OSError):
            st.warning('Saved history could not be read. Searches still work; the existing file has not been replaced.')
            entries = []
        if entries:
            st.caption(f'{len(entries)} saved search(es) · up to 50 recent entries')
            by_id = {entry.id: entry for entry in entries}
            kinds = {'recovery': 'Dataset', 'papers': 'Papers', 'paper_datasets': 'Paper datasets'}
            selected = st.selectbox('Saved searches', list(by_id), key='history_selection',
                format_func=lambda identifier: kinds[by_id[identifier].kind] + ' · ' +
                    by_id[identifier].created_at[:16].replace('T', ' ') + ' UTC · ' + by_id[identifier].label[:100])
            entry = by_id[selected]
            uploaded = entry.kind == 'paper_datasets' and entry.request.get('paper', {}).get('id', '').startswith('uploaded-pdf:')
            if st.button('View saved results', key='history_view', width='stretch'):
                try: _view(entry, render_report, expected_scope=access.scope)
                except HistoryError: st.error('This saved result cannot be opened.')
            st.caption(SAMPLE_DISCLOSURE)
            if st.button('Search again', key='history_rerun', width='stretch',
                         disabled=uploaded,
                         help='Makes new service requests using the recorded input. A PDF recovery reruns its selected URL, not the upload.'):
                try:
                    with st.spinner('Running the recorded search again…'):
                        fresh, saved, live_result = _search_again(entry.id, access.scope)
                    _view(fresh, render_report, expected_scope=access.scope, saved=saved, live_result=live_result)
                except Exception:
                    logging.getLogger(__name__).exception('Saved search rerun failed')
                    st.error('The search could not be rerun or saved. Existing history was kept.')
                finally:
                    rerun_if_identity_changed(access.scope)
            if uploaded: st.caption('Upload the original PDF again to refresh this saved identification; PDF text/files are not stored.')
            if st.button('Delete selected search', key='history_delete', width='stretch'):
                try:
                    authorized_store(access.scope).delete(entry.id)
                    st.rerun()
                except HistoryError: st.error('The saved search could not be deleted.')
            export_entries = authorized_store(access.scope).list()
            json_download('Export history (.json)', json.dumps(
                {'version': 1, 'entries': [asdict(item) for item in export_entries]}, ensure_ascii=False, allow_nan=False),
                file_name='relink-search-history.json', key='history_export')
        else:
            st.caption('No saved searches are available yet.')
        if st.button('Clear saved history', key='history_clear', width='stretch'):
            try:
                authorized_store(access.scope).clear()
                st.rerun()
            except HistoryError: st.error('Saved history could not be cleared.')
