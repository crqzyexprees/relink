"""Thin presentation of bounded samples and cached candidate pagination."""
import hashlib
import streamlit as st

from relink.workflow import public_link

SAMPLE_DISCLOSURE = ('Dataset searches send your query and public metadata to Google, plus an advertised CSV/TSV '
    'header and up to three rows when available. At most three files are sampled, 64 KiB each. '
    'Use nonconfidential data; samples do not verify the complete dataset.')


def render_assessment(assessment, *, key_prefix):
    if assessment is None: return
    st.caption('Dataset AI · ' + assessment.status.replace('_', ' ') + (' · ' + assessment.model if assessment.model else ''))
    st.text(assessment.detail)
    if assessment.status not in ('ranked', 'not_found'):
        st.info('Existing matching evidence remains available; AI relevance is unavailable for this search.')
    if assessment.retry_after: st.text('Retry-After: ' + assessment.retry_after)
    for warning in assessment.warnings: st.text(warning)
    samples = [p for p in assessment.previews if p.status != 'metadata_only']
    skipped = len(assessment.previews) - len(samples)
    if skipped: st.caption(f'{skipped} candidate(s) used metadata only; no supported advertised CSV/TSV file was sampled.')
    if samples:
        with st.expander('Inspect bounded dataset samples'):
            st.caption('Header and up to three rows, at most 64 KiB per file. These samples do not verify the full dataset.')
            for index, sample in enumerate(samples):
                st.text(sample.candidate_id)
                st.text(sample.status.replace('_', ' ') + ' · ' + sample.detail)
                st.text(sample.url)
                safe = public_link(sample.url)
                if safe: st.link_button('Open sampled source', safe, key=f'{key_prefix}_preview_{index}')
                st.caption(f'{sample.bytes_read} byte(s) read · {sample.retrieved_at}')
                if sample.headers: st.text('Columns: ' + ' · '.join(sample.headers))
                if sample.rows:
                    columns = [f'{i + 1}. {name}' for i, name in enumerate(sample.headers)]
                    st.dataframe([dict(zip(columns, row)) for row in sample.rows], hide_index=True, width='stretch')


def render_options(discovery, *, key_prefix, render_candidate, snapshot_id=''):
    render_assessment(discovery.assessment, key_prefix=key_prefix)
    rows = discovery.candidates
    if not rows: return
    st.subheader('Best-ranked options')
    assessed = discovery.assessment and discovery.assessment.status == 'ranked'
    st.caption(f'{len(rows)} candidate(s). ' + ('Combined order preserves identity/conflict safeguards, then uses AI relevance. '
        'Evidence points and verification statuses are unchanged.' if assessed else
        'The highest relevance score appears first; equal scores are ties, not stronger recommendations.'))
    if len(rows) == 1:
        st.caption('Only one candidate was returned by the sources. This is the only available lead, '
                   'not a comparison winner. Archive availability supplies at most one closest capture.')
    signature = hashlib.sha256(repr((snapshot_id, tuple((r.candidate.doi, r.candidate.url, r.candidate.archived_url) for r in rows))).encode()).hexdigest()
    state = key_prefix + '_visible'
    if st.session_state.get(key_prefix + '_snapshot') != signature:
        st.session_state[key_prefix + '_snapshot'] = signature
        st.session_state[state] = 10
    visible = st.session_state.get(state, 10)
    if visible < len(rows) and st.button('Load more datasets · next 10', key=key_prefix + '_load_more'):
        st.session_state[state] = min(visible + 10, len(rows))
        st.rerun()
    st.caption(f'Showing {min(visible, len(rows))} of {len(rows)} returned candidates. Load more makes no new requests.')
    for index, row in enumerate(rows[:visible], 1): render_candidate(index, row, key_prefix)
