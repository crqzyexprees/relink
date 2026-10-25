"""Bounded public OpenAlex retrieval; paper ranking lives outside this provider."""
from datetime import datetime, timezone
import json
import re

import httpx

from relink.identifiers import normalize_doi
from relink.network import PublicHTTPClient
from relink.paper_models import Paper, PaperProvenance


API = 'https://api.openalex.org/works'


def reconstruct_abstract(index) -> str:
    if index is None or index == {}:
        return ''
    if not isinstance(index, dict) or len(index) > 12000:
        raise ValueError('Invalid abstract inverted index.')
    positions = {}
    for word, offsets in index.items():
        if not isinstance(word, str) or not word or len(word) > 200 or not isinstance(offsets, list):
            raise ValueError('Invalid abstract token.')
        if len(offsets) > 12000:
            raise ValueError('Abstract token has too many positions.')
        for offset in offsets:
            if type(offset) is not int or not 0 <= offset < 12000 or offset in positions:
                raise ValueError('Invalid or repeated abstract position.')
            positions[offset] = word
    if positions and set(positions) != set(range(len(positions))):
        raise ValueError('Abstract positions are not contiguous.')
    abstract = ' '.join(positions[offset] for offset in range(len(positions)))
    if len(abstract) > 60000:
        raise ValueError('Abstract exceeds the text limit.')
    return abstract


def parse_paper(row: dict, retrieved_at: str) -> Paper:
    if not isinstance(row, dict) or not re.fullmatch(r'https://openalex\.org/W[0-9]+', str(row.get('id', ''))):
        raise ValueError('Invalid OpenAlex work identifier.')
    title = row.get('title')
    if not isinstance(title, str) or not title.strip() or len(title) > 4000:
        raise ValueError('Missing or invalid paper title.')
    abstract = reconstruct_abstract(row.get('abstract_inverted_index'))
    authors = []
    authorships = row.get('authorships')
    for authorship in authorships[:100] if isinstance(authorships, list) else []:
        author = authorship.get('author') if isinstance(authorship, dict) else None
        name = author.get('display_name') if isinstance(author, dict) else None
        if isinstance(name, str): authors.append(name[:300])
    year = row.get('publication_year')
    location = row.get('primary_location')
    location = location if isinstance(location, dict) else {}
    oa = row.get('best_oa_location')
    oa = oa if isinstance(oa, dict) else {}
    def text(value): return value if isinstance(value, str) and len(value) <= 4000 else ''
    landing_url = text(location.get('landing_page_url'))
    pdf_url = text(oa.get('pdf_url')) or text(location.get('pdf_url'))
    return Paper(id=row['id'], title=title, abstract=abstract, authors=tuple(authors),
                 year=year if type(year) is int and 1000 <= year <= 9999 else None,
                 doi=normalize_doi(row.get('doi')) or '', landing_url=landing_url, pdf_url=pdf_url,
                 retrieved_at=retrieved_at,
                 provenance=(PaperProvenance('openalex', row['id'], retrieved_at, landing_url, pdf_url),))


class OpenAlexProvider:
    def __init__(self, client: PublicHTTPClient):
        self.client = client
        self.has_more = False

    def search(self, terms: tuple[str, ...], *, page=1, limit=15):
        """Return (papers, query URL, warnings), raising typed request failures."""
        self.has_more = False
        if type(page) is not int or not 1 <= page <= 3 or type(limit) is not int or not 1 <= limit <= 15:
            raise ValueError('Paper retrieval is limited to three pages of 15 records per source.')
        expression = ' OR '.join('"' + term + '"' for term in terms)
        url = str(httpx.URL(API, params={'search.title_and_abstract': expression, 'per-page': str(limit), 'page': str(page),
            'select': 'id,title,doi,publication_year,authorships,abstract_inverted_index,primary_location,best_oa_location'}))
        response = self.client.fetch(url, read_body=True)
        if response.http_status == 429:
            raise OpenAlexError('rate_limited', 'OpenAlex rate limited or its free quota was exhausted. No automatic retry.',
                               url, response.headers.get('retry-after'))
        if response.http_status != 200:
            raise OpenAlexError('error', f'OpenAlex returned HTTP {response.http_status}.', url)
        try:
            payload = json.loads(response.body)
            rows = payload['results']
            if not isinstance(rows, list) or len(rows) > limit:
                raise ValueError('Too many work records.')
        except (ValueError, TypeError, KeyError, RecursionError):
            raise OpenAlexError('invalid_response', 'Malformed OpenAlex response.', url) from None
        self.has_more = len(rows) == limit
        papers, warnings = [], []
        retrieved_at = datetime.now(timezone.utc).isoformat()
        for row in rows:
            try: papers.append(parse_paper(row, retrieved_at))
            except ValueError as exc: warnings.append(str(exc))
        if rows and not papers:
            raise OpenAlexError('invalid_response', 'No usable OpenAlex work records.', url)
        return tuple(papers), url, tuple(warnings)


class OpenAlexError(Exception):
    def __init__(self, status, detail, url='', retry_after=None):
        super().__init__(detail)
        self.status, self.detail, self.url, self.retry_after = status, detail, url, retry_after
