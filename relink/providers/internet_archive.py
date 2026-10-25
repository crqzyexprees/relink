"""Internet Archive availability API adapter; returns metadata evidence only."""

from datetime import datetime, timezone
import json
import re

import httpx

from relink.models import CandidateProvenance, ProviderResult, RecoveryCandidate, SearchQuery, SearchResult
from relink.identifiers import normalize_url, url_filename
from relink.network import PublicHTTPClient, RequestFailure, validate_url


SOURCE = 'internet_archive'
AVAILABILITY_API = 'https://archive.org/wayback/available'


class InternetArchiveProvider:
    def __init__(self, client: PublicHTTPClient):
        self.client = client

    def search(self, original_url: str) -> ProviderResult:
        target = validate_url(original_url)
        request_url = httpx.URL(AVAILABILITY_API, params={'url': str(target)})
        try:
            response = self.client.fetch(str(request_url), read_body=True)
        except RequestFailure as exc:
            status = exc.status if exc.status in ('timeout', 'dns_failure', 'blocked') else 'error'
            return ProviderResult(status, SOURCE, detail=exc.detail)
        code = response.http_status
        if code == 429:
            return ProviderResult('rate_limited', SOURCE, detail='Archive API rate limited; no automatic retry.',
                                  http_status=code, retry_after=response.headers.get('retry-after'))
        if code != 200:
            return ProviderResult('error', SOURCE, detail=f'Archive API returned HTTP {code}.', http_status=code)
        try:
            payload = json.loads(response.body)
            snapshots = payload['archived_snapshots']
            if not isinstance(snapshots, dict):
                raise ValueError('Invalid snapshots object')
            if not snapshots:
                return ProviderResult('not_found', SOURCE, detail='No archived capture reported by the API.', http_status=code)
            closest = snapshots['closest']
            if closest.get('available') is False:
                return ProviderResult('not_found', SOURCE, detail='API reports no available closest capture.', http_status=code)
            if closest['available'] is not True or str(closest['status']) != '200':
                raise ValueError('Capture must be available with status 200')
            timestamp = closest['timestamp']
            if not isinstance(timestamp, str) or not re.fullmatch(r'[0-9]{14}', timestamp):
                raise ValueError('Invalid capture timestamp')
            datetime.strptime(timestamp, '%Y%m%d%H%M%S')
            archived = validate_url(closest['url'])
            prefix = f'/web/{timestamp}/'
            if archived.host != 'web.archive.org' or not archived.path.startswith(prefix):
                raise ValueError('Invalid archive replay URL')
            # Replay target must agree with the requested URL, including its query.
            embedded = str(archived).split(prefix, 1)[1]
            if normalize_url(str(validate_url(embedded))) != normalize_url(str(target)):
                raise ValueError('Archive replay target does not match the requested URL')
            candidate = RecoveryCandidate(
                original_url, closest['url'], timestamp, SOURCE,
                datetime.now(timezone.utc).isoformat(),
                ('Availability API: available=true; capture status=200.',
                 'Archive replay URL and timestamp agree with the requested URL.'),
                verification_status='archive_metadata_only', url=closest['url'],
                filenames=(url_filename(original_url),) if url_filename(original_url) else (),
                provenance=(CandidateProvenance(SOURCE, closest['url'], retrieved_at=datetime.now(timezone.utc).isoformat(),
                                                metadata=closest),),
            )
            return ProviderResult('found', SOURCE, candidate=candidate, http_status=code,
                                  detail='Capture reported by the availability API; contents unverified.')
        except (KeyError, TypeError, ValueError, AttributeError, RecursionError):
            return ProviderResult('invalid_response', SOURCE,
                                  detail='Archive API response is malformed or inconsistent; no candidate accepted.',
                                  http_status=code)

    def discover(self, query: SearchQuery) -> SearchResult:
        """Adapt the URL-only API to the shared discovery provider interface."""
        if not query.original_url:
            return SearchResult('not_applicable', SOURCE, detail='Archive discovery requires an original URL.')
        result = self.search(query.original_url)
        return SearchResult(result.status, SOURCE,
                            (result.candidate,) if result.candidate else (), result.detail,
                            result.http_status, result.retry_after)
