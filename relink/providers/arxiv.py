"""Official arXiv Atom API, bounded paging and process-wide serialized requests."""
from datetime import datetime, timezone
import re
from threading import Lock
import time
from urllib.parse import urlsplit
from xml.etree import ElementTree as ET

import httpx

from relink.identifiers import normalize_doi
from relink.paper_models import Paper, PaperProvenance


API = 'https://export.arxiv.org/api/query'
ATOM = '{http://www.w3.org/2005/Atom}'
ARXIV = '{http://arxiv.org/schemas/atom}'
_LOCK = Lock()
_LAST_REQUEST = float('-inf')


def arxiv_identifier(value):
    """Canonical work identity without the version; never trust arbitrary host IDs."""
    if not isinstance(value, str): return ''
    try:
        url = urlsplit(value)
        if url.scheme not in ('http', 'https') or url.hostname not in ('arxiv.org', 'www.arxiv.org'):
            return ''
        if url.username or url.password or url.port not in (None, 80, 443) or url.query or url.fragment: return ''
    except ValueError:
        return ''
    path = re.sub(r'^/(?:abs|pdf)/', '', url.path)
    path = re.sub(r'\.pdf$', '', path)
    if not re.fullmatch(r'(?:[0-9]{4}\.[0-9]{4,5}|[a-z-]+(?:\.[A-Z]{2})?/[0-9]{7})(?:v[1-9][0-9]*)?', path):
        return ''
    return re.sub(r'v[1-9][0-9]*$', '', path)


def _fetch(client, url):
    global _LAST_REQUEST
    # One API connection at a time across Streamlit sessions in this process.
    with _LOCK:
        delay = 3 - (time.monotonic() - _LAST_REQUEST)
        if delay > 0: time.sleep(delay)
        _LAST_REQUEST = time.monotonic()
        return client.fetch(url, read_body=True)


class ArxivError(Exception):
    def __init__(self, status, detail, url='', retry_after=None):
        super().__init__(detail)
        self.status, self.detail, self.url, self.retry_after = status, detail, url, retry_after


class ArxivProvider:
    def __init__(self, client):
        self.client = client
        self.has_more = False

    def search(self, terms, *, page=1, limit=15):
        self.has_more = False
        if type(page) is not int or not 1 <= page <= 3 or type(limit) is not int or not 1 <= limit <= 15:
            raise ValueError('Paper retrieval is limited to three pages of 15 records per source.')
        expression = ' OR '.join(f'(ti:"{term}" OR abs:"{term}")' for term in terms)
        url = str(httpx.URL(API, params={'search_query': expression, 'start': str((page - 1) * limit),
            'max_results': str(limit), 'sortBy': 'relevance', 'sortOrder': 'descending'}))
        response = _fetch(self.client, url)
        if response.http_status == 429:
            raise ArxivError('rate_limited', 'arXiv rate limited the search. No automatic retry.',
                             url, response.headers.get('retry-after'))
        if response.http_status != 200:
            raise ArxivError('error', f'arXiv returned HTTP {response.http_status}.', url)
        try:
            # Decode first so UTF-16/32 declarations cannot bypass the entity guard.
            body = response.body.decode('utf-8-sig')
            if '\x00' in body or '<!DOCTYPE' in body.upper() or '<!ENTITY' in body.upper(): raise ValueError()
            root = ET.fromstring(body)
            if root.tag != ATOM + 'feed': raise ValueError()
            rows = root.findall(ATOM + 'entry')
            if len(rows) > limit: raise ValueError()
        except (ValueError, UnicodeError, ET.ParseError):
            raise ArxivError('invalid_response', 'Malformed or unsafe arXiv Atom response.', url) from None
        self.has_more = len(rows) == limit
        papers, warnings = [], []
        timestamp = datetime.now(timezone.utc).isoformat()
        for row in rows:
            try:
                identifier = row.findtext(ATOM + 'id', '')
                canonical = arxiv_identifier(identifier)
                title = ' '.join(row.findtext(ATOM + 'title', '').split())
                abstract = ' '.join(row.findtext(ATOM + 'summary', '').split())
                if not canonical or not title or len(title) > 4000 or len(abstract) > 60000: raise ValueError()
                # Preserve returned version while normalizing the official host/scheme.
                version = re.search(r'v[1-9][0-9]*$', identifier)
                record_url = 'https://arxiv.org/abs/' + canonical + (version[0] if version else '')
                published = row.findtext(ATOM + 'published', '')
                year = int(published[:4]) if re.match(r'[12][0-9]{3}-', published) else None
                authors = tuple(' '.join(author.findtext(ATOM + 'name', '').split())[:300]
                                for author in row.findall(ATOM + 'author')[:100])
                pdf_url = ''
                for link in row.findall(ATOM + 'link'):
                    target = link.get('href', '')
                    if (link.get('title') == 'pdf' or link.get('type') == 'application/pdf') and arxiv_identifier(target) == canonical:
                        pdf_url = re.sub(r'^http:', 'https:', target)
                        break
                papers.append(Paper(record_url, title, abstract, authors, year,
                    normalize_doi(row.findtext(ARXIV + 'doi', '')) or '', record_url, pdf_url,
                    'arxiv', timestamp, canonical, (PaperProvenance('arxiv', record_url, timestamp, record_url, pdf_url),)))
            except (TypeError, ValueError):
                warnings.append('Skipped an invalid arXiv paper record.')
        if rows and not papers:
            raise ArxivError('invalid_response', 'No usable arXiv paper records.', url)
        return tuple(papers), url, tuple(warnings)
