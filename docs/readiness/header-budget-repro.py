"""Offline evidence that the fetch budget uses cooperative header checkpoints.

Run from project root:
    PYTHONPATH=. .venv/bin/python /tmp/relink_header_budget_repro.py

No sockets, sleeps, or real DNS requests are used. The fake backend delivers one
HTTP header byte per fake second; each read is within its unchanged timeout.
"""
from unittest.mock import patch

import httpx
from httpcore._backends.mock import MockStream

from relink.network import PublicHTTPClient, RequestFailure


def reproduce():
    clock = [0.0]
    read_timeouts = []

    class Stream(MockStream):
        def read(self, max_bytes, timeout=None):
            # Each individual read takes one fake second, less than timeout=3.
            clock[0] += 1.0
            read_timeouts.append(timeout)
            return super().read(max_bytes, timeout)

    class Backend:
        def connect_tcp(self, *args, **kwargs):
            header = b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n'
            return Stream([bytes([value]) for value in header])

    transport = httpx.HTTPTransport(
        trust_env=False, limits=httpx.Limits(max_keepalive_connections=0))
    transport._pool._network_backend = Backend()
    with patch('relink.network.monotonic', side_effect=lambda: clock[0]):
        with PublicHTTPClient(total_timeout=3, transport=transport,
                              resolver=lambda host, port: ['93.184.215.14']) as client:
            try:
                client.fetch('https://example.org/', read_body=True)
            except RequestFailure as exc:
                result = {'status': exc.status, 'detail': exc.detail,
                          'total_timeout': 3, 'fake_elapsed_seconds': clock[0],
                          'read_count': len(read_timeouts),
                          'read_timeout_values': sorted(set(read_timeouts))}
            else:
                raise AssertionError('Expected a timeout after headers completed.')
    assert result['status'] == 'timeout'
    assert result['fake_elapsed_seconds'] == 38.0
    assert result['read_timeout_values'] == [3.0]
    return result


if __name__ == '__main__':
    import json
    print(json.dumps(reproduce(), indent=2))
