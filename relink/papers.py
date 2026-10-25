"""Multi-source abstract retrieval/ranking and selected-paper dataset discovery."""
import re
import unicodedata

from relink.extraction import MAX_PDF_BYTES, PDFExtractionError, TextPage, extract_pdf_links, extract_text_links
from relink.gemini import identify_and_discover
from relink.gemini_config import GeminiSettings
from relink.identifiers import normalize_doi, normalize_url
from relink.models import SearchQuery, SearchResult
from relink.network import PublicHTTPClient, RequestFailure
from relink.paper_models import Paper, PaperDatasetLookup, PaperSearchResult, PaperProviderResult
from relink.paper_ranking import deduplicate_papers, keyword_rank, paper_identities
from relink.providers.arxiv import ArxivError, ArxivProvider
from relink.providers.datacite import DataCiteProvider
from relink.providers.gemini_ranking import GeminiPaperRanker
from relink.providers.openalex import OpenAlexError, OpenAlexProvider


STOP_WORDS = frozenset('a an the and or not of to in on for with by from at as is are was were be been '
    'this that these those it its we i you my our their they want would like about find show me '
    'paper papers study studies research using use used based approach approaches describe looking '
    'how what which can could should into through than also'.split())


def topic_terms(topic: str) -> tuple[str, ...]:
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 1200 or any(ord(c) < 32 and c not in '\n\t\r' for c in topic):
        raise ValueError('Describe a topic using 1–1,200 characters.')
    tokens = re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', topic).casefold())
    terms = tuple(dict.fromkeys(token for token in tokens if len(token) >= 2 and token not in STOP_WORDS))[:12]
    if not terms:
        raise ValueError('Include at least one meaningful topic keyword.')
    return terms


def search_papers(topic: str, *, client: PublicHTTPClient | None = None,
                  settings: GeminiSettings | None = None, batch: int = 0,
                  exclude_identifiers: tuple[str, ...] = ()) -> PaperSearchResult:
    terms = topic_terms(topic)
    if type(batch) is not int or not 0 <= batch < 3:
        raise ValueError('Paper search is limited to three batches per topic.')
    if not isinstance(exclude_identifiers, tuple) or len(exclude_identifiers) > 500 or any(
        not isinstance(value, str) or len(value) > 4000 for value in exclude_identifiers):
        raise ValueError('Invalid previous-paper identifiers.')
    if client is None:
        with PublicHTTPClient() as owned:
            return search_papers(topic, client=owned, settings=settings, batch=batch, exclude_identifiers=exclude_identifiers)
    records, providers, warnings = [], [], []
    for source, provider in (('openalex', OpenAlexProvider(client)), ('arxiv', ArxivProvider(client))):
        try:
            papers, query_url, notes = provider.search(terms, page=batch + 1, limit=15)
            records.extend(papers)
            warnings.extend(source + ': ' + note for note in notes)
            providers.append(PaperProviderResult(source, 'found' if papers else 'not_found',
                query_url=query_url, count=len(papers), has_more=provider.has_more))
        except (RequestFailure, OpenAlexError, ArxivError) as exc:
            providers.append(PaperProviderResult(source, exc.status, exc.detail, getattr(exc, 'url', ''),
                                                 retry_after=getattr(exc, 'retry_after', None)))
    unique = deduplicate_papers(records, terms)
    seen = set(exclude_identifiers)
    unseen = tuple(paper for paper in unique if not paper_identities(paper) & seen)
    for paper in unique: seen.update(paper_identities(paper))
    missing = sum(not paper.abstract.strip() for paper in unique)
    candidates = tuple(keyword_rank(paper, terms) for paper in unseen if paper.abstract.strip())
    config = settings or GeminiSettings()
    ranked, ranking = GeminiPaperRanker(client, api_key=config.api_key, model=config.model).rank(topic, candidates)
    if ranking.status != 'ranked':
        ranked = tuple(sorted((item for item in candidates if item.matched_terms), key=lambda item: (-item.score, item.paper.id)))
    errors = [p for p in providers if p.status not in ('found', 'not_found')]
    successful = len(providers) - len(errors)
    if ranked:
        status = 'partial' if errors else 'found'
    elif errors:
        status = 'partial' if successful else errors[0].status
    else:
        status = 'not_found'
    return PaperSearchResult(status, ranked,
        f'Batch {batch + 1}: up to 30 unique papers from OpenAlex and arXiv. Rankings apply only to this batch; '
        'relevance is not paper quality, verification or a calibrated probability.',
        providers[0].query_url, len(unique), missing, tuple(warnings),
        next((p.retry_after for p in errors if p.retry_after), None), ranking, tuple(providers), batch,
        batch < 2 and any(p.has_more for p in providers), tuple(sorted(seen)))


def lookup_paper_datasets(paper: Paper, *, client: PublicHTTPClient | None = None,
                          settings: GeminiSettings | None = None) -> PaperDatasetLookup:
    if client is None:
        with PublicHTTPClient(max_body_bytes=MAX_PDF_BYTES) as owned:
            return lookup_paper_datasets(paper, client=owned, settings=settings)
    datasets = (DataCiteProvider(client, limit=10).discover(SearchQuery(doi=paper.doi)) if paper.doi else
                SearchResult('not_applicable', 'datacite', detail='This paper has no DOI for related-dataset lookup.'))
    links = {link.url: link for link in extract_text_links(paper.abstract)}
    pages = (TextPage(0, paper.abstract),) if paper.abstract.strip() else ()
    status, detail = 'unavailable', 'No public PDF URL was advertised. You can upload a legally obtained PDF in Find datasets.'
    if paper.pdf_url:
        try:
            response = client.fetch(paper.pdf_url, read_body=True)
            if response.http_status != 200:
                status = 'rate_limited' if response.http_status == 429 else 'unavailable'
                detail = f'Paper PDF returned HTTP {response.http_status}; no paywall bypass attempted.'
                if response.headers.get('retry-after'):
                    detail += ' Retry-After: ' + response.headers['retry-after']
            else:
                extraction = extract_pdf_links(response.body)
                pages = pages + extraction.pages
                status = 'extracted'
                detail = f'Parsed {extraction.page_count} PDF page(s); research links may include references rather than datasets.'
                if extraction.warnings: detail += ' ' + ' '.join(extraction.warnings)
                for link in extraction.links:
                    links.setdefault(link.url, link)
        except RequestFailure as exc:
            status, detail = exc.status, exc.detail
        except PDFExtractionError as exc:
            status, detail = 'invalid_pdf', str(exc)
    # Do not send the paper's own DOI/landing/PDF back as if it were a dataset link.
    own = {normalize_url(value) for value in (paper.id, paper.landing_url, paper.pdf_url,
           'https://doi.org/' + paper.doi if paper.doi else '')} - {None}
    paper_doi = normalize_doi(paper.doi)
    links = tuple(link for link in links.values() if normalize_url(link.url) not in own
                  and not (paper_doi and normalize_doi(link.url) == paper_doi))[:250]
    identification, searches = identify_and_discover(pages, settings=settings or GeminiSettings(), client=client)
    return PaperDatasetLookup(paper.id, datasets, links, status, detail, identification, searches)


def lookup_uploaded_datasets(extraction, *, paper_id: str, settings: GeminiSettings, client=None) -> PaperDatasetLookup:
    identification, searches = identify_and_discover(extraction.pages, settings=settings, client=client)
    return PaperDatasetLookup(paper_id, SearchResult('not_applicable', 'datacite',
        detail='No paper DOI was supplied; named datasets were searched separately.'), extraction.links,
        'extracted', f'Parsed {extraction.page_count} uploaded PDF page(s) in memory.', identification, searches)
