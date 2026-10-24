"""HTTP and DNS are mocked; these tests never query live services."""

import io
import json
import socket
import threading
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import httpx

from relink import network, recovery, verification
from relink.providers import internet_archive


ORIGINAL = 'https://example.org/data.zip'
CAPTURE = 'http://web.archive.org/web/20200102030405/https://example.org/data.zip'
PAYLOAD = {'archived_snapshots': {'closest': {
    'available': True, 'url': CAPTURE, 'timestamp': '20200102030405', 'status': '200',
}}}


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        # Unexpected real DNS access must fail even if a test is misconfigured.
        self.dns_guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in test'))
        self.dns_guard.start()
        self.addCleanup(self.dns_guard.stop)

    def client(self, handler, resolver=None, **options):
        client = network.PublicHTTPClient(
            transport=httpx.MockTransport(handler),
            resolver=resolver or (lambda host, port: ['93.184.215.14']),
            **options,
        )
        self.addCleanup(client.close)
        return client

    def test_reports_capture_without_claiming_dataset_preservation(self):
        def handler(request):
            if request.headers['host'] == 'archive.org':
                self.assertEqual(request.url.params['url'], ORIGINAL)
                return httpx.Response(200, json=PAYLOAD)
            return httpx.Response(404)

        result = recovery.recover_url(ORIGINAL, client=self.client(handler))
        self.assertEqual(result.original_url, ORIGINAL)
        self.assertEqual(result.current.status, 'not_found')
        self.assertEqual(result.current.http_status, 404)
        self.assertEqual(result.archive.status, 'found')
        candidate = result.archive.candidate
        self.assertEqual(candidate.archived_url, CAPTURE)
        self.assertEqual(candidate.original_url, ORIGINAL)
        self.assertEqual(candidate.capture_timestamp, '20200102030405')
        self.assertEqual(candidate.source, 'internet_archive')
        self.assertEqual(candidate.verification_status, 'archive_metadata_only')
        self.assertIn('dataset', candidate.limitation.lower())
        self.assertTrue(candidate.retrieved_at.endswith('+00:00'))

    def test_current_http_statuses_stay_distinct(self):
        for code, expected in [(200, 'working'), (204, 'working'), (404, 'not_found'),
                               (403, 'forbidden'), (429, 'rate_limited'),
                               (500, 'http_error'), (410, 'http_error')]:
            with self.subTest(code=code):
                client = self.client(lambda r: httpx.Response(code, headers={'Retry-After': '120'}))
                result = verification.check_current_url(ORIGINAL, client)
                self.assertEqual(result.status, expected)
                self.assertEqual(result.http_status, code)
                if code == 429:
                    self.assertEqual(result.retry_after, '120')

    def test_redirects_preserve_original_and_report_final_status(self):
        def handler(request):
            if request.url.path == '/data.zip':
                return httpx.Response(302, headers={'Location': '/moved.zip'})
            return httpx.Response(200)
        result = verification.check_current_url(ORIGINAL, self.client(handler))
        self.assertEqual(result.status, 'working')
        self.assertEqual(result.final_url, 'https://example.org/moved.zip')
        self.assertEqual(result.redirects, ('https://example.org/moved.zip',))

    def test_current_timeout_still_searches_archive(self):
        def handler(request):
            if request.headers['host'] == 'archive.org':
                return httpx.Response(200, json=PAYLOAD)
            raise httpx.ReadTimeout('slow', request=request)
        result = recovery.recover_url(ORIGINAL, client=self.client(handler))
        self.assertEqual(result.current.status, 'timeout')
        self.assertEqual(result.archive.status, 'found')

    def test_dns_failure_still_searches_archive(self):
        def resolve(host, port):
            if host == 'example.org':
                raise socket.gaierror(socket.EAI_NONAME, 'not found')
            return ['93.184.215.14']
        result = recovery.recover_url(ORIGINAL, client=self.client(
            lambda r: httpx.Response(200, json=PAYLOAD), resolve))
        self.assertEqual(result.current.status, 'dns_failure')
        self.assertEqual(result.archive.status, 'found')

    def test_connect_error_is_not_mislabeled_dns_failure(self):
        def handler(request):
            raise httpx.ConnectError('connection refused', request=request)
        result = verification.check_current_url(ORIGINAL, self.client(handler))
        self.assertEqual(result.status, 'network_error')

    def test_missing_archive_is_not_found(self):
        for payload in [{'archived_snapshots': {}},
                        {'archived_snapshots': {'closest': {'available': False}}}]:
            with self.subTest(payload=payload):
                result = internet_archive.InternetArchiveProvider(self.client(
                    lambda r: httpx.Response(200, json=payload))).search(ORIGINAL)
                self.assertEqual(result.status, 'not_found')
                self.assertIsNone(result.candidate)

    def test_bad_api_responses_are_errors_not_not_found(self):
        responses = [httpx.Response(500), httpx.Response(403), httpx.Response(200, text='oops'),
                     httpx.Response(200, json={}), httpx.Response(200, json=[]),
                     httpx.Response(200, json={'archived_snapshots': []})]
        for response in responses:
            with self.subTest(response=response):
                result = internet_archive.InternetArchiveProvider(self.client(lambda r: response)).search(ORIGINAL)
                self.assertIn(result.status, ('error', 'invalid_response'))
                self.assertIsNone(result.candidate)

    def test_archive_timeout(self):
        def handler(request):
            raise httpx.ConnectTimeout('slow', request=request)
        result = internet_archive.InternetArchiveProvider(self.client(handler)).search(ORIGINAL)
        self.assertEqual(result.status, 'timeout')
        self.assertIsNone(result.candidate)

    def test_archive_rate_limit_exposes_retry_after_without_retrying(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(429, headers={'Retry-After': '60'})
        result = internet_archive.InternetArchiveProvider(self.client(handler)).search(ORIGINAL)
        self.assertEqual(result.status, 'rate_limited')
        self.assertEqual(result.retry_after, '60')
        self.assertEqual(len(calls), 1)
        self.assertIsNone(result.candidate)

    def test_malformed_capture_cannot_create_candidate(self):
        changes = [{'url': 'https://evil.example/capture'}, {'timestamp': 'bad'},
                   {'timestamp': '20209999030405'}, {'status': '404'},
                   {'available': 'true'}, {'url': CAPTURE.replace('20200102', '20210102')},
                   {'url': CAPTURE.replace('example.org/data.zip', 'other.org/data.zip')},
                   {'url': 'https://web.archive.org.evil.example/web/capture'}]
        for change in changes:
            with self.subTest(change=change):
                closest = dict(PAYLOAD['archived_snapshots']['closest'], **change)
                result = internet_archive.InternetArchiveProvider(self.client(lambda r: httpx.Response(
                    200, json={'archived_snapshots': {'closest': closest}}))).search(ORIGINAL)
                self.assertEqual(result.status, 'invalid_response')
                self.assertIsNone(result.candidate)

    def test_internal_and_invalid_inputs_never_make_http_requests(self):
        inputs = ['http://localhost/', 'http://LOCALHOST./', 'http://host.local/',
                  'http://127.0.0.1/', 'http://10.0.0.1/', 'http://169.254.169.254/',
                  'http://[::1]/', 'http://[fec0::1]/', 'http://[::ffff:127.0.0.1]/', 'http://224.0.0.1/',
                  'file:///etc/passwd', 'ftp://example.org/x', 'https://user:pass@example.org/',
                  'https://example.org:8443/', 'https://example.org/\nfoo',
                  'https://example.org\\@127.0.0.1/', 'http://intranet/']
        def handler(request):
            self.fail('Unsafe URL reached HTTP transport')
        for url in inputs:
            with self.subTest(url=url), self.assertRaises(network.UnsafeURLError):
                recovery.recover_url(url, client=self.client(handler))

    def test_any_private_dns_answer_blocks_request_and_archive_lookup(self):
        def handler(request):
            self.fail('Private DNS answer reached HTTP transport')
        result = recovery.recover_url(ORIGINAL, client=self.client(
            handler, lambda h, p: ['93.184.215.14', '10.1.2.3']))
        self.assertEqual(result.current.status, 'blocked')
        self.assertEqual(result.archive.status, 'blocked')

    def test_unsafe_redirects_are_never_requested(self):
        for target in ['http://127.0.0.1/', 'http://169.254.169.254/',
                       'file:///etc/passwd', 'http://example.org/insecure',
                       'https://internal.example.org/']:
            calls = []
            def handler(request):
                calls.append(request)
                return httpx.Response(302, headers={'Location': target})
            def resolve(host, port):
                return ['10.1.2.3'] if host == 'internal.example.org' else ['93.184.215.14']
            with self.subTest(target=target):
                result = verification.check_current_url(ORIGINAL, self.client(handler, resolve))
                self.assertEqual(result.status, 'blocked')
                self.assertEqual(len(calls), 1)

    def test_redirect_loop_and_limit_are_bounded(self):
        for mode in ['loop', 'limit']:
            calls = []
            def handler(request):
                calls.append(request)
                target = ORIGINAL if mode == 'loop' else f'/next/{len(calls)}'
                return httpx.Response(302, headers={'Location': target})
            with self.subTest(mode=mode):
                result = verification.check_current_url(ORIGINAL, self.client(handler, max_redirects=2))
                self.assertEqual(result.status, 'redirect_error')
                self.assertLessEqual(len(calls), 3)

    def test_public_connection_is_pinned_with_original_host_and_tls_name(self):
        observed = []
        def handler(request):
            observed.append(request)
            return httpx.Response(200)
        result = verification.check_current_url(ORIGINAL, self.client(handler))
        self.assertEqual(result.status, 'working')
        self.assertEqual(observed[0].url.host, '93.184.215.14')
        self.assertEqual(observed[0].headers['host'], 'example.org')
        self.assertEqual(observed[0].extensions['sni_hostname'], 'example.org')
        self.assertTrue(all(value > 0 for value in observed[0].extensions['timeout'].values()))

    def test_api_redirect_is_public_validated_too(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(302, headers={'Location': 'http://127.0.0.1/'})
        result = internet_archive.InternetArchiveProvider(self.client(handler)).search(ORIGINAL)
        self.assertEqual(result.status, 'blocked')
        self.assertEqual(len(calls), 1)

    def test_api_body_size_is_bounded(self):
        result = internet_archive.InternetArchiveProvider(self.client(
            lambda r: httpx.Response(200, content=b'x' * 100), max_body_bytes=64)).search(ORIGINAL)
        self.assertEqual(result.status, 'error')
        self.assertIsNone(result.candidate)

    def test_current_check_does_not_download_response_body(self):
        class UnreadableBody(httpx.SyncByteStream):
            def __iter__(self):
                raise AssertionError('Current URL body downloaded')
        result = verification.check_current_url(ORIGINAL, self.client(
            lambda r: httpx.Response(200, stream=UnreadableBody())))
        self.assertEqual(result.status, 'working')

    def test_dns_timeout_is_distinct_from_dns_failure(self):
        def resolve(host, port):
            raise TimeoutError('DNS timed out')
        result = verification.check_current_url(ORIGINAL, self.client(lambda r: httpx.Response(200), resolve))
        self.assertEqual(result.status, 'timeout')

    def test_default_resolver_bounds_a_stalled_dns_lookup(self):
        released = threading.Event()
        def stalled(*args, **kwargs):
            released.wait(2)
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.215.14', 443))]
        try:
            with patch('socket.getaddrinfo', side_effect=stalled):
                with self.assertRaises(TimeoutError):
                    network.resolve_addresses('example.org', 443, timeout=0.01)
        finally:
            released.set()

    def test_default_resolver_preserves_dns_failure(self):
        with patch('socket.getaddrinfo', side_effect=socket.gaierror(socket.EAI_NONAME, 'not found')):
            with self.assertRaises(socket.gaierror):
                network.resolve_addresses('example.org', 443)

    def test_redirect_without_location_is_explicit_error(self):
        result = verification.check_current_url(ORIGINAL, self.client(lambda r: httpx.Response(302)))
        self.assertEqual(result.status, 'redirect_error')

    def test_streamed_api_body_limit_closes_response(self):
        class LargeBody(httpx.SyncByteStream):
            closed = False
            def __iter__(self):
                yield b'x' * 40
                yield b'x' * 40
                raise AssertionError('Response consumed beyond limit')
            def close(self):
                self.closed = True
        body = LargeBody()
        result = internet_archive.InternetArchiveProvider(self.client(
            lambda r: httpx.Response(200, stream=body), max_body_bytes=64)).search(ORIGINAL)
        self.assertEqual(result.status, 'error')
        self.assertTrue(body.closed)

    def test_cli_rejects_unsafe_input(self):
        from scripts.recover_url import main
        output = io.StringIO()
        with redirect_stdout(output):
            code = main(['http://localhost/'])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(output.getvalue())['error'], 'unsafe_url')

    def test_cli_prints_json_with_mocked_services(self):
        from scripts.recover_url import main
        client = self.client(lambda r: httpx.Response(200, json=PAYLOAD))
        output = io.StringIO()
        with patch('scripts.recover_url.recover_url', side_effect=lambda url: recovery.recover_url(url, client=client)):
            with redirect_stdout(output):
                code = main([ORIGINAL])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())['archive']['status'], 'found')


if __name__ == '__main__':
    unittest.main()
