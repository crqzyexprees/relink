"""Conservative identifier normalization; original values stay in provenance."""

import re
from urllib.parse import unquote, urlsplit

import httpx


def normalize_doi(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.strip()
    value = re.sub(r'^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)', '', value, flags=re.I)
    if re.fullmatch(r'10\.[0-9]{4,9}/[^\s?#]+', value):
        return value.casefold()
    return None


def normalize_url(value: str | None) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        url = httpx.URL(value)
        if url.scheme not in ('http', 'https') or not url.host or url.userinfo:
            return None
        # HTTP origin-form requests use '/' for an empty root path. Preserve
        # meaningful non-root slashes, escaped path separators, and query strings.
        if url.path == '/':
            url = url.copy_with(path='/')
        path, separator, query = url.raw_path.partition(b'?')

        def path_escape(match):
            character = chr(int(match.group(1), 16))
            # Decode safe unreserved path characters only. Keep encoded dots
            # to avoid creating dot segments, and preserve query bytes exactly.
            if character.isascii() and (character.isalnum() or character in '-_~'):
                return character.encode('ascii')
            return b'%' + match.group(1).upper()

        path = re.sub(rb'%([0-9a-fA-F]{2})', path_escape, path)
        url = url.copy_with(raw_path=path + separator + query)
        return str(url.copy_with(fragment=None))
    except (httpx.InvalidURL, ValueError):
        return None


def url_filename(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        name = unquote(urlsplit(value).path.rsplit('/', 1)[-1])
    except ValueError:
        return None
    return name if '.' in name and name not in ('.', '..') else None
