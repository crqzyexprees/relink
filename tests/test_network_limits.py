"""Offline connection-origin and elapsed-budget regressions using real HTTPX."""
import unittest
from unittest.mock import patch

import httpx
from httpcore._backends.mock import MockStream

from relink.network import PublicHTTPClient, RequestFailure


class NetworkLimitTests(unittest.TestCase):
    def test_same_ip_origins_each_receive_their_own_tls_handshake(self):
        handshakes = []
        class Stream(MockStream):
            def start_tls(self, ssl_context, server_hostname=None, timeout=None):
                handshakes.append(server_hostname)
                return self
        class Backend:
            def connect_tcp(self, *args, **kwargs):
                return Stream([b'HTTP/1.1 200 OK\r\nContent-Length: 0\r\n\r\n'] * 2)
        transport_type = httpx.HTTPTransport
        def transport_factory(**kwargs):
            transport = transport_type(**kwargs)
            transport._pool._network_backend = Backend()
            return transport
        with patch('relink.network.httpx.HTTPTransport', side_effect=transport_factory):
            with PublicHTTPClient(resolver=lambda h, p: ['93.184.215.14']) as client:
                client.fetch('https://first.example/a', read_body=True)
                client.fetch('https://second.example/b', read_body=True)
        self.assertEqual(handshakes, ['first.example', 'second.example'])

    def test_slow_incremental_body_hits_total_budget(self):
        clock = [0.0]
        class SlowStream(httpx.SyncByteStream):
            def __iter__(self):
                for _ in range(10):
                    clock[0] += 1
                    yield b'x'
        with patch('relink.network.monotonic', side_effect=lambda: clock[0], create=True):
            with PublicHTTPClient(total_timeout=3, transport=httpx.MockTransport(
                lambda r: httpx.Response(200, stream=SlowStream())), resolver=lambda h, p: ['93.184.215.14']) as client:
                with self.assertRaises(RequestFailure) as caught:
                    client.fetch('https://example.org/', read_body=True)
        self.assertEqual(caught.exception.status, 'timeout')
        self.assertLessEqual(clock[0], 4)

    def test_redirects_share_one_budget_and_remaining_io_timeout_shrinks(self):
        clock, timeouts, calls = [0.0], [], []
        def handler(request):
            calls.append(request.url.path)
            timeouts.append(request.extensions['timeout']['read'])
            clock[0] += 2
            return httpx.Response(302, headers={'Location': '/next' + str(len(calls))})
        with patch('relink.network.monotonic', side_effect=lambda: clock[0], create=True):
            with PublicHTTPClient(total_timeout=3, transport=httpx.MockTransport(handler),
                                  resolver=lambda h, p: ['93.184.215.14']) as client:
                with self.assertRaises(RequestFailure) as caught: client.fetch('https://example.org/')
        self.assertEqual(caught.exception.status, 'timeout')
        self.assertEqual(timeouts, [3, 1])
        self.assertEqual(len(calls), 2)

    def test_bad_total_budgets_are_rejected_before_network(self):
        for value in (0, -1, float('inf'), float('nan')):
            with self.subTest(value=value), self.assertRaises(ValueError): PublicHTTPClient(total_timeout=value)
