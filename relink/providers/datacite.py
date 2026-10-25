"""Bounded, unauthenticated dataset searches against the public DataCite API."""

from datetime import datetime, timezone
import json
import re

import httpx

from relink.identifiers import normalize_doi, url_filename
from relink.models import Candidate, CandidateProvenance, RelatedIdentifier, SearchQuery, SearchResult
from relink.network import PublicHTTPClient, RequestFailure


SOURCE = 'datacite'
API = 'https://api.datacite.org/dois'


def _quoted(value: str) -> str:
    # Treat user text as a literal phrase, never as a query-string expression.
    return '"' + re.sub(r'([+\-=!(){}\[\]^"~*?:\\/|&<>])', r'\\\1', value.strip()) + '"'


def _words(value: str, operator: str = 'AND') -> str:
    words = re.findall(r'\w+', value, flags=re.UNICODE)
    if not words:
        raise ValueError('Title/description must contain searchable words.')
    return '(' + f' {operator} '.join(word + '*' for word in words) + ')'


def build_query(query: SearchQuery) -> str:
    clauses = []
    if query.title.strip():
        clauses.append('titles.title:' + _words(query.title))
    if query.author.strip():
        # Names are commonly stored as "Family, Given"; token order must not matter.
        clauses.append('creators.name:' + _words(query.author))
    if query.institution.strip():
        phrase = _quoted(query.institution)
        clauses.append('(' + ' OR '.join(field + ':' + phrase for field in (
            'creators.affiliation.name', 'contributors.affiliation.name', 'creators.name',
            'publisher.name', 'publisher')) + ')')
    if query.year is not None:
        clauses.append(f'publicationYear:{query.year}')
    if query.original_url and not (query.doi and normalize_doi(query.original_url) == normalize_doi(query.doi)):
        phrase = _quoted(query.original_url)
        clauses.append('(' + ' OR '.join(field + ':' + phrase for field in (
            'url', 'identifiers.identifier', 'alternateIdentifiers.alternateIdentifier',
            'relatedIdentifiers.relatedIdentifier')) + ')')
    if query.doi:
        doi = normalize_doi(query.doi)
        prefix, suffix = doi.split('/', 1)
        clauses.append(f'((prefix:{_quoted(prefix)} AND suffix:{_quoted(suffix)}) OR '
                       f'relatedIdentifiers.relatedIdentifier:{_quoted(doi)} OR '
                       f'relatedIdentifiers.relatedIdentifier:{_quoted("https://doi.org/" + doi)})')
    if query.description.strip():
        words = _words(query.description, 'OR')
        clauses.append(f'(descriptions.description:{words} OR titles.title:{words})')
    if query.filenames:
        clauses.append('(' + ' OR '.join('identifiers.identifier:' + _quoted(name)
                                       for name in query.filenames) + ')')
    return ' AND '.join(clauses)


def _text(value) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _objects(value) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _unique(values) -> tuple:
    return tuple(dict.fromkeys(value for value in values if value))


def parse_record(row: dict, original_url: str, retrieved_at: str) -> Candidate:
    if not isinstance(row, dict) or row.get('type') != 'dois':
        raise ValueError('Invalid DOI resource.')
    attributes = row.get('attributes')
    if not isinstance(attributes, dict):
        raise ValueError('Missing DOI attributes.')
    doi = _text(attributes.get('doi')) or _text(row.get('id'))
    if not normalize_doi(doi):
        raise ValueError('Missing or malformed DOI.')
    if row.get('id') and normalize_doi(row['id']) != normalize_doi(doi):
        raise ValueError('Record DOI and id disagree.')
    types = attributes.get('types')
    if not isinstance(types, dict) or str(types.get('resourceTypeGeneral', '')).casefold() != 'dataset':
        raise ValueError('Record is not explicitly a dataset.')
    creators = _objects(attributes.get('creators'))
    contributors = _objects(attributes.get('contributors'))
    authors = _unique(_text(item.get('name')) or _text(' '.join(filter(None, (
        _text(item.get('givenName')), _text(item.get('familyName')))))) for item in creators)
    institutions = []
    for person in creators + contributors:
        affiliations = person.get('affiliation')
        if not isinstance(affiliations, list):
            affiliations = []
        for affiliation in affiliations:
            institutions.append(_text(affiliation.get('name')) if isinstance(affiliation, dict) else _text(affiliation))
        if person.get('nameType') == 'Organizational':
            institutions.append(_text(person.get('name')))
    related = [RelatedIdentifier(item['relatedIdentifier'], str(item.get('relatedIdentifierType', '')),
                                  str(item.get('relationType', ''))) for item in _objects(attributes.get('relatedIdentifiers'))
               if _text(item.get('relatedIdentifier'))]
    for name, value_key, type_key in [('identifiers', 'identifier', 'identifierType'),
                                       ('alternateIdentifiers', 'alternateIdentifier', 'alternateIdentifierType')]:
        related.extend(RelatedIdentifier(item[value_key], str(item.get(type_key, '')), 'AlternateIdentifier')
                       for item in _objects(attributes.get(name)) if _text(item.get(value_key)))
    year = attributes.get('publicationYear')
    year = int(year) if type(year) in (int, str) and re.fullmatch(r'[0-9]{4}', str(year)) else None
    url = _text(attributes.get('url'))
    publisher = attributes.get('publisher')
    publisher = _text(publisher.get('name')) if isinstance(publisher, dict) else _text(publisher)
    content_urls = attributes.get('contentUrl') or []
    if isinstance(content_urls, str):
        content_urls = [content_urls]
    if not isinstance(content_urls, list):
        content_urls = []
    filenames = _unique([url_filename(url), *(url_filename(item) for item in content_urls),
                         *(item.identifier for item in related if item.identifier_type.casefold() in ('filename', 'file name'))])
    return Candidate(
        original_url=original_url, source=SOURCE, retrieved_at=retrieved_at,
        url=url, doi=doi,
        titles=_unique(_text(item.get('title')) for item in _objects(attributes.get('titles'))),
        authors=authors, institutions=_unique(institutions), publisher=publisher, year=year, filenames=filenames,
        descriptions=_unique(_text(item.get('description')) for item in _objects(attributes.get('descriptions'))),
        version=_text(attributes.get('version')), related_identifiers=tuple(related),
        evidence=('DataCite reports DOI metadata with resourceTypeGeneral=Dataset.',),
        provenance=(CandidateProvenance(SOURCE, url, doi, str(row.get('id', doi)), retrieved_at, attributes),),
    )


class DataCiteProvider:
    def __init__(self, client: PublicHTTPClient, *, limit: int = 20,
                 page_size: int = 20, max_pages: int = 2):
        if any(type(value) is not int for value in (limit, page_size, max_pages)) or not (
            1 <= limit <= 100 and 1 <= page_size <= 25 and 1 <= max_pages <= 5
        ):
            raise ValueError('Use limit 1–100, page size 1–25, and page count 1–5.')
        self.client, self.limit, self.page_size, self.max_pages = client, limit, page_size, max_pages

    def discover(self, query: SearchQuery) -> SearchResult:
        expression = build_query(query)
        candidates = []
        warnings = []
        request_url = None
        more = False
        seen = 0
        for page in range(1, self.max_pages + 1):
            request_url = str(httpx.URL(API, params={
                'query': expression, 'resource-type-id': 'dataset', 'page[number]': str(page), 'sort': 'relevance',
                'page[size]': str(min(self.page_size, self.limit)), 'affiliation': 'true',
                'detail': 'true', 'fields[dois]': 'doi,url,titles,creators,contributors,publisher,publicationYear,'
                'descriptions,types,version,relatedIdentifiers,identifiers,alternateIdentifiers,contentUrl,dates,rightsList',
            }))
            def failure(status, detail, code=None, retry_after=None):
                return SearchResult('partial' if candidates else status, SOURCE, tuple(candidates),
                                    detail, code, retry_after, request_url, True if candidates else False, tuple(warnings))
            try:
                response = self.client.fetch(request_url, read_body=True)
            except RequestFailure as exc:
                return failure(exc.status if exc.status in ('timeout', 'dns_failure', 'blocked') else 'error', exc.detail)
            code = response.http_status
            if code == 429:
                return failure('rate_limited', 'DataCite rate limited; no automatic retry.', code,
                               response.headers.get('retry-after'))
            if code != 200:
                return failure('error', f'DataCite returned HTTP {code}.', code)
            try:
                payload = json.loads(response.body)
                rows = payload['data']
                if not isinstance(rows, list):
                    raise ValueError('Expected list of DOI records.')
            except (ValueError, TypeError, KeyError, RecursionError):
                return failure('invalid_response', 'Malformed DataCite list response.', code)
            retrieved_at = datetime.now(timezone.utc).isoformat()
            for index, row in enumerate(rows):
                if len(candidates) >= self.limit:
                    break
                try:
                    candidates.append(parse_record(row, query.original_url, retrieved_at))
                except ValueError as exc:
                    warnings.append(f'Page {page}, record {index + 1}: {exc}')
            seen += len(rows)
            meta = payload.get('meta')
            total = meta.get('total') if isinstance(meta, dict) else None
            if not rows and type(total) is int and seen < total:
                return failure('invalid_response', 'DataCite reports more results but returned an empty page.', code)
            links = payload.get('links')
            more = (seen < total) if type(total) is int else (
                bool(links.get('next')) if isinstance(links, dict) and 'next' in links else len(rows) >= min(self.page_size, self.limit))
            more = bool(rows) and (more or len(rows) > self.limit)
            if not more or len(candidates) >= self.limit:
                break
        status = 'partial' if candidates and warnings else 'found' if candidates else 'invalid_response' if warnings else 'not_found'
        return SearchResult(status, SOURCE, tuple(candidates),
                            'Metadata candidates only; downloadable content was not checked.',
                            200, query_url=request_url, truncated=more, warnings=tuple(warnings))
