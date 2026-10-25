"""Gemini uses mocked HTTP and locally checked paper text; no real keys here."""
from dataclasses import asdict
import json
import unittest
import os
from pathlib import Path
import tempfile
from unittest.mock import patch

import httpx

from relink.extraction import TextPage
from relink.gemini_config import GeminiSettings, load_gemini_settings, DEFAULT_MODEL
from relink.gemini import identify_and_discover
from relink.network import PublicHTTPClient, RequestFailure
from relink.providers.gemini import GeminiProvider
from tests.test_datacite import record


KEY = 'test-only-secret-never-live'
PAGES = (TextPage(1, 'We evaluate on the SQuAD 1.1 dataset. Results use the original evaluation split.'),)


def response(rows):
    return {'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
        {'text': json.dumps({'datasets': rows})}]}}]}


def mention(**changes):
    return {'name': 'SQuAD', 'version': '1.1', 'page': 1,
            'quote': 'We evaluate on the SQuAD 1.1 dataset.'} | changes


class GeminiTests(unittest.TestCase):
    def client(self, handler):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def test_structured_mentions_are_grounded_and_key_stays_out_of_urls_and_results(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json=response([mention()]))
        result = GeminiProvider(self.client(handler), api_key=KEY).identify(PAGES)
        self.assertEqual(result.status, 'found')
        self.assertEqual(result.mentions[0].name, 'SQuAD')
        self.assertEqual(result.mentions[0].page, 1)
        self.assertEqual(requests[0].method, 'POST')
        self.assertEqual(requests[0].headers['x-goog-api-key'], KEY)
        self.assertNotIn(KEY, str(requests[0].url))
        self.assertNotIn(KEY, requests[0].content.decode())
        self.assertNotIn(KEY, json.dumps(asdict(result)))
        self.assertIn('responseSchema', json.loads(requests[0].content)['generationConfig'])

    def test_fabricated_evidence_is_rejected_and_actual_source_excerpt_can_ground_a_name(self):
        rows = [mention(quote='This quote does not occur in the paper.'), mention(page=2),
                mention(name='InventedDataset'), mention(version='9.9'), mention(url='http://127.0.0.1/secret')]
        result = GeminiProvider(self.client(lambda r: httpx.Response(200, json=response(rows))), api_key=KEY).identify(PAGES)
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.mentions), 1)
        self.assertEqual(result.mentions[0].quote_source, 'local_text')
        self.assertIn(result.mentions[0].quote, PAGES[0].text)
        self.assertNotIn('does not occur', result.mentions[0].quote)
        self.assertTrue(result.warnings)

    def test_mixed_rows_keep_valid_quote_but_report_partial_and_deduplicate(self):
        result = GeminiProvider(self.client(lambda r: httpx.Response(200, json=response([
            mention(), mention(), mention(page=99)]))), api_key=KEY).identify(PAGES)
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.mentions), 1)

    def test_empty_missing_key_no_text_and_service_errors_stay_distinct(self):
        client = self.client(lambda r: self.fail('Missing-key/no-text must not call API'))
        self.assertEqual(GeminiProvider(client, api_key='').identify(PAGES).status, 'not_configured')
        self.assertEqual(GeminiProvider(client, api_key=KEY).identify(()).status, 'no_text')
        for code, expected, payload in [(200, 'not_found', response([])), (401, 'authentication_error', {}),
                                       (403, 'authentication_error', {}), (429, 'rate_limited', {}),
                                       (500, 'error', {}), (200, 'invalid_response', {})]:
            with self.subTest(code=code, expected=expected):
                result = GeminiProvider(self.client(lambda r: httpx.Response(code, json=payload,
                    headers={'Retry-After': '30'})), api_key=KEY).identify(PAGES)
                self.assertEqual(result.status, expected)
                self.assertFalse(result.mentions)
                self.assertNotIn(KEY, result.detail)

    def test_post_credentials_are_not_forwarded_through_redirects(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(307, headers={'Location': 'https://other.example/collect'})
        result = GeminiProvider(self.client(handler), api_key=KEY).identify(PAGES)
        self.assertEqual(len(calls), 1)
        self.assertEqual(result.status, 'redirect_error')

    def test_network_timeout_and_invalid_json_do_not_leak_key(self):
        def handler(request): raise httpx.ReadTimeout('mock timeout', request=request)
        result = GeminiProvider(self.client(handler), api_key=KEY).identify(PAGES)
        self.assertEqual(result.status, 'timeout')
        result = GeminiProvider(self.client(lambda r: httpx.Response(200, content=b'[' * 10000 + b']' * 10000)), api_key=KEY).identify(PAGES)
        self.assertEqual(result.status, 'invalid_response')

    def test_named_searches_use_only_real_datacite_responses_and_are_bounded(self):
        calls = []
        pages = (TextPage(1, 'We use SQuAD, MNIST, CIFAR, and Iris datasets.'),)
        rows = [mention(name=name, version='', quote=pages[0].text) for name in ('SQuAD', 'MNIST', 'CIFAR', 'Iris')]
        def handler(request):
            calls.append(request)
            if request.headers['host'] == 'generativelanguage.googleapis.com': return httpx.Response(200, json=response(rows))
            return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
        identification, searches = identify_and_discover(pages, settings=GeminiSettings(KEY), client=self.client(handler))
        self.assertEqual(identification.status, 'found')
        self.assertEqual(len(searches), 3)
        self.assertEqual(len(calls), 4)
        self.assertEqual(searches[0].result.candidates[0].doi, '10.1234/soil.v1')
        self.assertNotEqual(searches[0].ranked[0].status, 'verified_exact_match')

    def test_request_text_and_response_size_limits(self):
        received = []
        def handler(request):
            received.append(json.loads(request.content))
            return httpx.Response(200, json=response([]))
        pages = tuple(TextPage(i, 'some public research text ' * 2000) for i in range(1, 8))
        GeminiProvider(self.client(handler), api_key=KEY).identify(pages)
        supplied = json.loads(received[0]['contents'][0]['parts'][0]['text'])['pages']
        self.assertLessEqual(sum(len(page['text']) for page in supplied), 48000)
        self.assertNotIn(KEY, json.dumps(received))

    def test_credential_post_rejects_http_and_does_not_leak_header_to_later_gets(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=response([]))
        client = self.client(handler)
        with self.assertRaises(RequestFailure):
            client.post_json('http://example.org/', {}, headers={'x-goog-api-key': KEY})
        self.assertFalse(calls)
        GeminiProvider(client, api_key=KEY).identify(PAGES)
        client.fetch('https://example.org/')
        self.assertNotIn('x-goog-api-key', calls[-1].headers)
        with self.assertRaises(RequestFailure):
            client.post_json('https://example.org/', {'text': 'x' * (256 * 1024)}, headers={'x-goog-api-key': KEY})

    def test_config_uses_private_file_or_environment_without_exposing_key(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'secrets.toml'
            path.write_text('GEMINI_API_KEY = "' + KEY + '"\n')
            with patch.dict(os.environ, {'GEMINI_API_KEY': '', 'GEMINI_MODEL': ''}):
                settings = load_gemini_settings(path)
            self.assertEqual(settings.api_key, KEY)
            self.assertEqual(settings.model, DEFAULT_MODEL)
            self.assertNotIn(KEY, repr(settings))
            with patch.dict(os.environ, {'GEMINI_API_KEY': 'environment-test-key'}):
                self.assertEqual(load_gemini_settings(path).api_key, 'environment-test-key')
            path.write_text('{invalid TOML')
            with patch.dict(os.environ, {'GEMINI_API_KEY': ''}):
                self.assertEqual(load_gemini_settings(path).api_key, '')

    def test_partial_name_cannot_be_grounded_inside_a_different_dataset(self):
        pages = (TextPage(1, 'We use Fashion-MNIST as the benchmark dataset.'),)
        result = GeminiProvider(self.client(lambda r: httpx.Response(200, json=response([
            mention(name='MNIST', version='', quote='invented quote with MNIST here')]))), api_key=KEY).identify(pages)
        self.assertEqual(result.status, 'invalid_response')
        self.assertFalse(result.mentions)

    def test_unsearchable_model_name_cannot_discard_independent_paper_results(self):
        from relink.paper_models import Paper
        from relink.papers import lookup_paper_datasets
        from tests.pdf_fixtures import make_pdf
        text = 'The ++ dataset contains public observations.'
        def handler(request):
            if request.headers['host'] == 'generativelanguage.googleapis.com':
                return httpx.Response(200, json=response([mention(name='++', version='', quote=text)]))
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(200, content=make_pdf(text))
        result = lookup_paper_datasets(Paper('https://openalex.org/W1', 'Paper', doi='10.1234/paper',
            pdf_url='https://example.org/paper.pdf'), client=self.client(handler), settings=GeminiSettings(KEY))
        self.assertEqual(result.datasets.status, 'found')
        self.assertEqual(result.pdf_status, 'extracted')
        self.assertEqual(result.identification.status, 'invalid_response')
        self.assertFalse(result.named_searches)
