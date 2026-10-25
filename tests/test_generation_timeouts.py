"""Mocked generation delays: no sleeps, live DNS or real API credentials."""
import unittest
from unittest.mock import Mock, patch

import httpx

from relink.network import PublicHTTPClient, RequestFailure
from relink.providers.gemini import GeminiProvider
from relink.providers.gemini_ranking import GeminiPaperRanker
from tests.test_gemini import PAGES, mention, response as dataset_response
from tests.test_gemini_ranking import paper, response as ranking_response


class GenerationTimeoutTests(unittest.TestCase):
    def client(self, handler):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def test_generation_can_finish_after_ordinary_url_timeout(self):
        calls = []
        def handler(request):
            calls.append(request)
            # Mock a model that needs 20 seconds before yielding a response.
            if request.extensions['timeout']['read'] < 20:
                raise httpx.ReadTimeout('Simulated slow generation', request=request)
            return ranking_response([{'id': 'p001', 'evidence_id': 1, 'reason': 'Actual source methods.'}])
        ranked, info = GeminiPaperRanker(self.client(handler), api_key='mock-only').rank('methods', (paper(),))
        self.assertEqual(info.status, 'ranked')
        self.assertEqual(len(ranked), 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].extensions['timeout']['read'], 60)
        self.assertEqual(calls[0].extensions['timeout']['connect'], 10)

    def test_dataset_identification_uses_the_same_bounded_generation_allowance(self):
        calls = []
        def handler(request):
            calls.append(request)
            if request.extensions['timeout']['read'] < 20:
                raise httpx.ReadTimeout('Simulated slow identification', request=request)
            return httpx.Response(200, json=dataset_response([mention()]))
        found = GeminiProvider(self.client(handler), api_key='mock-only').identify(PAGES)
        self.assertEqual(found.status, 'found')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].extensions['timeout']['read'], 60)

    def test_post_override_does_not_change_later_url_checks_or_default_posts(self):
        calls = []
        client = self.client(lambda request: calls.append(request) or httpx.Response(200, json={}))
        with patch('relink.network.monotonic', return_value=100):
            client.fetch('https://example.org/')
            client.post_json('https://example.org/generate', {}, read_timeout=60, total_timeout=90)
            client.fetch('https://example.org/')
            client.post_json('https://example.org/ordinary', {})
        self.assertEqual([r.extensions['timeout']['read'] for r in calls], [10, 60, 10, 10])
        self.assertEqual([r.extensions['relink_deadline'] for r in calls], [130, 190, 130, 130])
        for request in calls:
            self.assertEqual(request.extensions['timeout']['connect'], 10)
            self.assertEqual(request.extensions['timeout']['write'], 10)
            self.assertEqual(request.extensions['timeout']['pool'], 10)

    def test_custom_elapsed_budget_clamps_read_and_still_expires(self):
        clock = Mock(return_value=100)
        def handler(request):
            self.assertEqual(request.extensions['timeout']['read'], 20)
            self.assertEqual(request.extensions['relink_deadline'], 120)
            clock.return_value = 121
            return httpx.Response(200, json={})
        with patch('relink.network.monotonic', clock), self.assertRaises(RequestFailure) as caught:
            self.client(handler).post_json('https://example.org/generate', {}, read_timeout=60, total_timeout=20)
        self.assertEqual(caught.exception.status, 'timeout')

    def test_invalid_overrides_do_not_make_requests_or_disable_limits(self):
        client = self.client(lambda r: self.fail('Invalid limits must not make requests'))
        for field in ('read_timeout', 'total_timeout'):
            for value in (0, -1, float('nan'), float('inf'), '60', True):
                with self.subTest(field=field, value=str(value)), self.assertRaises(ValueError):
                    client.post_json('https://example.org/generate', {}, **{field: value})

    def test_genuine_generation_timeout_still_falls_back_without_retry(self):
        calls = []
        def handler(request):
            calls.append(request)
            raise httpx.ReadTimeout('mock-only key must not escape', request=request)
        ranked, info = GeminiPaperRanker(self.client(handler), api_key='mock-only').rank('methods', (paper(),))
        self.assertEqual(info.status, 'timeout')
        self.assertFalse(ranked)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('mock-only', info.detail)
