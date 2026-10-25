"""Public-only HTTP with vetted, pinned IPs and explicit redirect handling."""

from dataclasses import dataclass
import ipaddress
import math
import json
import queue
import socket
import threading
from time import monotonic
from collections.abc import Callable

import httpx


Resolver = Callable[[str, int], list[str]]


class UnsafeURLError(ValueError):
    """The URL or one of its DNS answers is not a public web address."""


class RequestFailure(Exception):
    def __init__(self, status: str, detail: str, url: str, redirects: tuple[str, ...]):
        super().__init__(detail)
        self.status = status
        self.detail = detail
        self.url = url
        self.redirects = redirects


def _public_ip(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    if not ip.is_global or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return False
    if isinstance(ip, ipaddress.IPv6Address):
        # Disallow scoped and transition addresses that can embed private IPv4.
        if ip.is_site_local or ip.scope_id or ip.ipv4_mapped or ip.sixtofour or ip.teredo:
            return False
        if ip in ipaddress.ip_network('64:ff9b::/96') or ip in ipaddress.ip_network('64:ff9b:1::/48'):
            return False
    else:
        # Conservative exclusions, including ranges misclassified by older Python.
        if ip in ipaddress.ip_network('192.0.0.0/24') or ip in ipaddress.ip_network('192.88.99.0/24'):
            return False
    return True


def validate_url(value: str) -> httpx.URL:
    """Validate syntax and literal addresses; DNS is checked at connection time."""
    if not isinstance(value, str) or not value or len(value) > 8192:
        raise UnsafeURLError('Supply an HTTP(S) URL of at most 8192 characters.')
    if '\\' in value or any(ord(c) <= 32 or ord(c) == 127 for c in value):
        raise UnsafeURLError('URL contains whitespace, controls, or backslashes.')
    try:
        url = httpx.URL(value)
        host = url.host.rstrip('.').lower()
        if url.scheme not in ('http', 'https') or not host or url.userinfo:
            raise UnsafeURLError('Only HTTP(S) URLs without credentials are allowed.')
        if url.port not in (None, 80 if url.scheme == 'http' else 443):
            raise UnsafeURLError('Only the standard HTTP and HTTPS ports are allowed.')
        if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.lan', '.home')):
            raise UnsafeURLError('Local and internal hostnames are blocked.')
        try:
            ipaddress.ip_address(host)
        except ValueError:
            if '.' not in host or '%' in host:
                raise UnsafeURLError('Use a public, fully qualified hostname.')
        else:
            if not _public_ip(host):
                raise UnsafeURLError('Non-public IP addresses are blocked.')
        return url.copy_with(fragment=None)
    except (httpx.InvalidURL, ValueError) as exc:
        if isinstance(exc, UnsafeURLError):
            raise
        raise UnsafeURLError('Malformed web URL.') from exc


def resolve_addresses(host: str, port: int, timeout: float = 10.0) -> list[str]:
    """Bound the caller's wait for OS DNS; a stuck resolver cannot block exit."""
    try:
        ipaddress.ip_address(host)
        return [host]
    except ValueError:
        pass
    result: queue.Queue = queue.Queue(maxsize=1)

    def lookup():
        try:
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            result.put([item[4][0] for item in addresses])
        except OSError as exc:
            result.put(exc)

    threading.Thread(target=lookup, daemon=True).start()
    try:
        addresses = result.get(timeout=timeout)
    except queue.Empty as exc:
        raise TimeoutError('DNS resolution timed out.') from exc
    if isinstance(addresses, OSError):
        raise addresses
    if not addresses:
        raise socket.gaierror(socket.EAI_NONAME, 'No DNS answers.')
    return list(dict.fromkeys(addresses))


class PublicTransport(httpx.BaseTransport):
    """Resolve once, reject mixed public/private answers, and connect by IP.

    Host and TLS SNI remain the original hostname. Connecting by the validated IP
    prevents a second DNS lookup from redirecting a connection to an internal IP.
    The injectable transport/resolver are trusted dependencies for offline tests.
    """

    def __init__(self, transport: httpx.BaseTransport, resolver: Resolver | None = None):
        self._transport = transport
        self._resolver = resolver

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        url = validate_url(str(request.url))
        port = url.port or (443 if url.scheme == 'https' else 80)
        if self._resolver is not None:
            addresses = self._resolver(url.host, port)
        else:
            timeout = request.extensions.get('timeout', {}).get('connect', 10.0)
            deadline = request.extensions.get('relink_deadline')
            if deadline is not None:
                timeout = min(timeout, deadline - monotonic())
            if timeout <= 0:
                raise TimeoutError('Request time budget exhausted before DNS.')
            addresses = resolve_addresses(url.host, port, timeout)
        if not addresses:
            raise socket.gaierror(socket.EAI_NONAME, 'No DNS answers.')
        if not all(_public_ip(address) for address in addresses):
            raise UnsafeURLError('DNS returned a non-public address; request blocked.')
        headers = request.headers.copy()
        headers['Host'] = url.netloc.decode('ascii')
        pinned = httpx.Request(
            request.method, url.copy_with(host=addresses[0]), headers=headers,
            stream=request.stream,
            extensions={**request.extensions, 'sni_hostname': url.host},
        )
        return self._transport.handle_request(pinned)

    def close(self):
        self._transport.close()


@dataclass(frozen=True)
class FetchResult:
    http_status: int
    final_url: str
    redirects: tuple[str, ...]
    headers: httpx.Headers
    body: bytes


class PublicHTTPClient:
    """Public HTTP with inactivity limits and cooperative elapsed-budget checks.

    total_timeout is checked between redirects and response-body chunks. It does
    not preempt HTTPX's internal header-reading loop or native code. A strict
    wall-clock deadline requires lower-level cancellation, not just this budget.
    No automatic retries or environment proxies are used.
    """

    def __init__(self, *, timeout: float = 10.0, max_redirects: int = 5,
                 total_timeout: float = 30.0,
                 max_body_bytes: int = 1_048_576,
                 transport: httpx.BaseTransport | None = None,
                 resolver: Resolver | None = None):
        if (not math.isfinite(timeout) or timeout <= 0 or not math.isfinite(total_timeout)
                or total_timeout <= 0 or max_redirects < 0 or max_body_bytes <= 0):
            raise ValueError('Timeout/body limit must be positive; redirect limit nonnegative.')
        self.max_redirects = max_redirects
        self.max_body_bytes = max_body_bytes
        self.timeout, self.total_timeout = timeout, total_timeout
        self._client = httpx.Client(
            transport=PublicTransport(
                # Pool origins are IP-pinned. Reusing a connection for another
                # hostname on that IP would bypass its independent TLS handshake.
                transport or httpx.HTTPTransport(retries=0, trust_env=False,
                    limits=httpx.Limits(max_keepalive_connections=0)), resolver),
            timeout=httpx.Timeout(timeout), follow_redirects=False, trust_env=False,
            headers={'User-Agent': 'ReLink/0.1 (academic dataset recovery)',
                     'Accept-Encoding': 'identity'},
        )

    def fetch(self, value: str, *, read_body: bool = False) -> FetchResult:
        return self._request('GET', value, read_body=read_body)

    def post_json(self, value: str, payload: dict, *, headers: dict | None = None,
                  read_timeout: float | None = None, total_timeout: float | None = None) -> FetchResult:
        """HTTPS POST with optional per-request generation budgets; no shared mutation."""
        for limit in (read_timeout, total_timeout):
            if limit is not None and (type(limit) not in (int, float) or not math.isfinite(limit) or limit <= 0):
                raise ValueError('Request timeout overrides must be finite positive seconds.')
        encoded = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(encoded) > 256 * 1024:
            raise RequestFailure('blocked', 'API request exceeds the size limit.', value, ())
        return self._request('POST', value, read_body=True, payload=payload, headers=headers,
                             read_timeout=read_timeout, total_timeout=total_timeout)

    def _request(self, method: str, value: str, *, read_body: bool, payload=None, headers=None,
                 read_timeout=None, total_timeout=None) -> FetchResult:
        url = value
        redirects: list[str] = []
        visited: set[str] = set()
        deadline = monotonic() + (self.total_timeout if total_timeout is None else total_timeout)

        def remaining():
            budget = deadline - monotonic()
            if budget <= 0:
                raise RequestFailure('timeout', 'Request exceeded its total time budget.', url, tuple(redirects))
            return budget

        try:
            while True:
                budget = remaining()
                parsed = validate_url(url)
                if method == 'POST' and parsed.scheme != 'https':
                    raise UnsafeURLError('Authenticated API requests require HTTPS.')
                url = str(parsed)
                if url in visited:
                    raise RequestFailure('redirect_error', 'Redirect loop detected.', url, tuple(redirects))
                visited.add(url)
                # Do not send cookies collected by previous requests or redirect hops.
                self._client.cookies.clear()
                options = {'json': payload, 'headers': headers} if method == 'POST' else {}
                request_timeout = httpx.Timeout(min(self.timeout, budget),
                    read=min(self.timeout if read_timeout is None else read_timeout, budget))
                with self._client.stream(method, parsed, timeout=request_timeout, **options,
                                         extensions={'relink_deadline': deadline}) as response:
                    remaining()
                    if method == 'POST' and 300 <= response.status_code < 400:
                        raise RequestFailure('redirect_error', 'API POST redirect rejected; credentials were not forwarded.',
                                             url, tuple(redirects))
                    if response.status_code in (301, 302, 303, 307, 308):
                        location = response.headers.get('location')
                        if not location:
                            raise RequestFailure('redirect_error', 'Redirect has no Location.', url, tuple(redirects))
                        if len(redirects) >= self.max_redirects:
                            raise RequestFailure('redirect_error', 'Redirect limit exceeded.', url, tuple(redirects))
                        # Validate the raw header before URL joining can normalize controls.
                        if '\\' in location or any(ord(c) <= 32 or ord(c) == 127 for c in location):
                            raise UnsafeURLError('Unsafe redirect Location.')
                        target = validate_url(str(parsed.join(location)))
                        if parsed.scheme == 'https' and target.scheme != 'https':
                            raise UnsafeURLError('HTTPS-to-HTTP redirect blocked.')
                        url = str(target)
                        redirects.append(url)
                        continue
                    body = bytearray()
                    if read_body and 200 <= response.status_code < 300:
                        if response.headers.get('content-encoding', 'identity').lower() != 'identity':
                            raise RequestFailure('network_error', 'Compressed API response rejected.', url, tuple(redirects))
                        # MockTransport may provide an already buffered response.
                        chunks = [response.content] if response.is_stream_consumed else response.iter_raw()
                        for chunk in chunks:
                            remaining()
                            limit = min(self.max_body_bytes, 256 * 1024) if method == 'POST' else self.max_body_bytes
                            if len(body) + len(chunk) > limit:
                                raise RequestFailure('network_error', 'API response exceeds size limit.', url, tuple(redirects))
                            body.extend(chunk)
                    return FetchResult(response.status_code, url, tuple(redirects),
                                       response.headers, bytes(body))
        except UnsafeURLError as exc:
            raise RequestFailure('blocked', str(exc), url, tuple(redirects)) from exc
        except (TimeoutError, httpx.TimeoutException) as exc:
            raise RequestFailure('timeout', 'DNS or HTTP request timed out.', url, tuple(redirects)) from exc
        except socket.gaierror as exc:
            raise RequestFailure('dns_failure', 'DNS resolution failed.', url, tuple(redirects)) from exc
        except (httpx.HTTPError, OSError) as exc:
            raise RequestFailure('network_error', f'Network request failed ({type(exc).__name__}).', url, tuple(redirects)) from exc
        except httpx.InvalidURL as exc:
            raise RequestFailure('blocked', 'Malformed redirect URL.', url, tuple(redirects)) from exc

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
