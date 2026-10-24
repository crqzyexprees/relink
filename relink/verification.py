"""Current URL access checks; these do not verify dataset preservation."""

from relink.models import CurrentStatus
from relink.network import PublicHTTPClient, RequestFailure


def check_current_url(url: str, client: PublicHTTPClient) -> CurrentStatus:
    try:
        response = client.fetch(url)
    except RequestFailure as exc:
        return CurrentStatus(exc.status, exc.url, redirects=exc.redirects, detail=exc.detail)
    code = response.http_status
    status = {404: 'not_found', 403: 'forbidden', 429: 'rate_limited'}.get(code)
    if status is None:
        status = 'working' if 200 <= code < 300 else 'http_error'
    return CurrentStatus(
        status, response.final_url, code, response.redirects,
        response.headers.get('retry-after') if code == 429 else None,
        'HTTP access status only; response body and dataset identity were not checked.',
    )
