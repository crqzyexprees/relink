"""Abstract keyword ranking and explicit selected-paper dataset discovery."""
import re
import unicodedata

from relink.extraction import MAX_PDF_BYTES, PDFExtractionError, TextPage, extract_pdf_links, extract_text_links
from relink.gemini import identify_and_discover
from relink.gemini_config import GeminiSettings
from relink.identifiers import normalize_doi, normalize_url
from relink.models import SearchQuery, SearchResult
from relink.network import PublicHTTPClient, RequestFailure
from relink.paper_models import Paper, PaperDatasetLookup, PaperSearchResult, RankedPaper
from relink.providers.datacite import DataCiteProvider
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


def search_papers(topic: str, *, client: PublicHTTPClient | None = None) -> PaperSearchResult:
    terms = topic_terms(topic)
    if client is None:
        with PublicHTTPClient() as owned:
            return search_papers(topic, client=owned)
    try:
        papers, query_url, warnings = OpenAlexProvider(client).search(terms)
    except RequestFailure as exc:
        return PaperSearchResult(exc.status, detail=exc.detail)
    except OpenAlexError as exc:
        return PaperSearchResult(exc.status, detail=exc.detail, query_url=exc.url, retry_after=exc.retry_after)
    ranked = []
    missing = sum(not paper.abstract for paper in papers)
    for paper in papers:
        words = set(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', paper.abstract).casefold()))
        matched = tuple(term for term in terms if term in words)
        if matched:
            ranked.append(RankedPaper(paper, len(matched) * 10, matched, terms))
    ranked.sort(key=lambda item: (-item.score, item.paper.id))
    unique, seen = [], set()
    for item in ranked:
        identity = item.paper.doi or item.paper.id
        if identity not in seen:
            unique.append(item)
            seen.add(identity)
    return PaperSearchResult('found' if unique else 'not_found', tuple(unique[:10]),
        'Abstract keyword matches among up to 25 retrieved records; points are not probabilities or quality ratings.',
        query_url, len(papers), missing, warnings)


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
