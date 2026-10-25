"""Bounded samples from advertised public CSV/TSV resources only.

A sample describes a prefix, never dataset identity or complete preservation.
There is no HTML crawling, filename guessing, archive extraction, or retry.
"""
from dataclasses import replace
from datetime import datetime, timezone
import codecs
import csv
import io
from urllib.parse import urlsplit

from relink.dataset_models import DatasetPreview
from relink.network import PublicHTTPClient, RequestFailure


MAX_PREVIEW_BYTES = 65_536
MAX_PREVIEW_ROWS = 3
MAX_PREVIEW_COLUMNS = 32
MAX_PREVIEW_CELL_CHARS = 240
_BOUNDS = ('Sample only: at most 64 KiB, header and 3 complete rows, 32 columns, '
           '240 characters per cell. Dataset identity and full-file preservation remain unverified.')


def _direct_url(candidate) -> str:
    """Use only URLs actually advertised by a candidate or DataCite record."""
    options = [candidate.url, candidate.archived_url]
    for provenance in candidate.provenance:
        if provenance.source.casefold() != 'datacite' or not isinstance(provenance.metadata, dict):
            continue
        content_urls = provenance.metadata.get('contentUrl', [])
        if isinstance(content_urls, str):
            options.append(content_urls)
        elif isinstance(content_urls, (list, tuple)):
            options.extend(content_urls)
    for value in options:
        if not isinstance(value, str):
            continue
        try:
            if urlsplit(value).path.casefold().endswith(('.csv', '.tsv')):
                return value
        except ValueError:
            continue
    return ''


def _record_prefix(text: str, delimiter: str, truncated: bool) -> tuple[str, bool]:
    """Find complete logical records before parsing, stopping after four.

    Quote boundaries follow CSV fields; malformed quoting in selected records is
    rejected. At a byte cap the trailing record is discarded, even if unquoted.
    """
    quoted = False
    after_quote = False
    field_start = True
    end = 0
    records = 0
    i = 0
    while i < len(text):
        char = text[i]
        if quoted:
            if char == '"':
                if i + 1 < len(text) and text[i + 1] == '"':
                    i += 2
                    continue
                quoted, after_quote = False, True
        elif char in '\r\n':
            if char == '\r' and i + 1 < len(text) and text[i + 1] == '\n':
                i += 1
            end = i + 1
            records += 1
            after_quote, field_start = False, True
            if records == MAX_PREVIEW_ROWS + 1:
                return text[:end], bool(text[end:])
        elif char == delimiter:
            after_quote, field_start = False, True
        elif char == '"':
            if not field_start:
                raise ValueError('Malformed quote inside an unquoted field.')
            quoted, field_start = True, False
        else:
            if after_quote:
                raise ValueError('Unexpected text after a closing quote.')
            field_start = False
        i += 1
    if truncated:
        return text[:end], bool(text[end:])
    if quoted:
        raise ValueError('Unterminated quoted record.')
    return text, False


def _sample(body: bytes, delimiter: str, truncated: bool):
    decoder = codecs.getincrementaldecoder('utf-8-sig')(errors='strict')
    text = decoder.decode(body, final=not truncated)
    if any(ord(char) < 32 and char not in '\r\n\t' for char in text):
        raise ValueError('Binary or control characters are not supported.')
    if text.lstrip().startswith('<'):
        raise ValueError('HTML/XML content is not a CSV/TSV sample.')
    selected, extra_records = _record_prefix(text, delimiter, truncated)
    records = list(csv.reader(io.StringIO(selected, newline=''), delimiter=delimiter, strict=True))
    if not records or len(records[0]) < 2 or not any(cell.strip() for cell in records[0]):
        raise ValueError('No complete delimited header with at least two columns.')
    width = len(records[0])
    if any(len(row) != width for row in records[1:]):
        raise ValueError('Sample rows do not match the header column count.')
    bounded = extra_records or width > MAX_PREVIEW_COLUMNS or any(
        len(cell) > MAX_PREVIEW_CELL_CHARS for row in records for cell in row)
    clipped = tuple(tuple(cell[:MAX_PREVIEW_CELL_CHARS] for cell in row[:MAX_PREVIEW_COLUMNS])
                    for row in records)
    return clipped[0], clipped[1:], bounded


def _metadata(headers, code, redirects):
    # Only provenance needed for the sample; never preserve cookies or tokens.
    metadata = {'http_status': code, 'redirects': list(redirects)}
    for name in ('content-type', 'content-length', 'content-range', 'retry-after'):
        if name in headers:
            metadata[name.replace('-', '_')] = headers[name][:500]
    return metadata


def preview_candidate(candidate, *, client: PublicHTTPClient) -> DatasetPreview:
    """Attempt at most one actual direct URL; keep metadata-only fallback explicit."""
    url = _direct_url(candidate)
    if not url:
        return DatasetPreview('metadata_only', detail=(
            'No advertised direct CSV/TSV URL; metadata only. ' + _BOUNDS))
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        result = client.fetch_prefix(url, max_bytes=MAX_PREVIEW_BYTES)
    except RequestFailure as exc:
        preview = DatasetPreview(exc.status, url=exc.url, retrieved_at=started_at,
            bytes_read=len(exc.body), detail=exc.detail + ' ' + _BOUNDS,
            truncated=bool(exc.body), response_metadata=_metadata(exc.headers, exc.http_status, exc.redirects))
        # An interrupted prefix can still retain earlier complete records. Its
        # failure status remains visible; invalid ranges/content are never parsed.
        if exc.body and exc.status in ('timeout', 'network_error'):
            try:
                header, rows, _ = _sample(exc.body, '\t' if urlsplit(url).path.casefold().endswith('.tsv') else ',', True)
            except (ValueError, UnicodeError, csv.Error):
                return preview
            return replace(preview, headers=header, rows=rows)
        return preview
    preview = DatasetPreview('sampled', url=result.final_url, retrieved_at=started_at,
        bytes_read=len(result.body), detail=_BOUNDS, truncated=result.truncated,
        response_metadata=_metadata(result.headers, result.http_status, result.redirects))
    if result.http_status not in (200, 206):
        status = {429: 'rate_limited', 404: 'not_found', 410: 'not_found',
                  401: 'blocked', 403: 'blocked'}.get(result.http_status, 'error')
        return replace(preview, status=status, detail=f'Preview returned HTTP {result.http_status}. ' + _BOUNDS)
    if result.headers.get('content-type', '').split(';', 1)[0].strip().casefold() in (
            'text/html', 'application/xhtml+xml', 'application/xml', 'text/xml', 'application/json'):
        return replace(preview, status='invalid_response', detail='Response is not CSV/TSV content. ' + _BOUNDS)
    try:
        header, rows, bounded = _sample(result.body,
            '\t' if urlsplit(url).path.casefold().endswith('.tsv') else ',', result.truncated)
    except (ValueError, UnicodeError, csv.Error) as exc:
        return replace(preview, status='invalid_response', detail=f'No usable CSV/TSV sample: {exc} ' + _BOUNDS)
    return replace(preview, headers=header, rows=rows, truncated=preview.truncated or bounded)
