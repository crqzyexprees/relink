"""Display grounded mention evidence separately from real repository candidates."""
import streamlit as st

from relink.workflow import public_link


def render_identification(identification, searches, *, key_prefix='dataset_ai', show_candidates=True):
    if identification is None: return
    st.subheader('Datasets mentioned in the paper')
    st.text('Gemini identification: ' + identification.status.replace('_', ' '))
    st.text(identification.detail)
    if identification.status not in ('found', 'partial', 'not_found'):
        st.warning('AI identification did not complete. Independent repository/link results remain available.')
    if identification.retry_after: st.text('Retry-After: ' + identification.retry_after)
    if identification.model:
        st.caption('Model: ' + identification.model + ' · Checked: ' + identification.retrieved_at)
    for warning in identification.warnings: st.text(warning)
    if identification.status == 'not_found':
        st.info('No supported dataset mentions were identified in the supplied excerpts. Other pages may contain more.')
    for mention in identification.mentions:
        with st.container(border=True):
            st.text(mention.name + (' · version ' + mention.version if mention.version else ''))
            st.caption(('Abstract' if mention.page == 0 else f'PDF page {mention.page}') +
                       ' · Quote checked against supplied text; dataset identity and study use remain unverified.')
            if mention.quote_source == 'local_text':
                st.caption('The AI quote was rejected; this excerpt was extracted directly from the paper at the dataset name.')
            st.text(mention.quote)
    for group_index, search in enumerate(searches, 1):
        st.subheader('Repository search: ' + search.mention.name)
        result = search.result
        st.text('DataCite: ' + result.status.replace('_', ' ') + ' · ' + result.detail)
        if result.retry_after: st.text('Retry-After: ' + result.retry_after)
        if result.truncated: st.caption('The repository result set was limited; more candidates may exist.')
        for warning in result.warnings: st.text(warning)
        for index, ranked in enumerate(search.ranked if show_candidates else (), 1):
            candidate = ranked.candidate
            with st.container(border=True):
                st.text(candidate.titles[0] if candidate.titles else 'Repository dataset record')
                st.caption(f'Option {index} · {ranked.score} relevance points · ' + ranked.status.replace('_', ' '))
                st.text(candidate.limitation)
                st.text('Source: DataCite')
                if candidate.doi: st.text('DOI: ' + candidate.doi)
                for label, value in [('Repository', candidate.url),
                                     ('DOI record', 'https://doi.org/' + candidate.doi if candidate.doi else '')]:
                    safe = public_link(value)
                    if safe:
                        st.link_button('Open ' + label, safe, key=f'{key_prefix}_{group_index}_{index}_{label}')
                with st.expander('Ranking and original source evidence'):
                    for evidence in ranked.explanation: st.text(evidence.detail)
                    for provenance in candidate.provenance: st.json(provenance.metadata, expanded=False)
    if len(identification.mentions) > len(searches):
        st.caption('Repository lookup is bounded to the first three supported names per action.')
