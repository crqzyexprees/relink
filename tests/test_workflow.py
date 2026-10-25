"""Real workflow adapter with mocked provider requests."""

import json
import importlib.util
import unittest
from unittest.mock import patch

import httpx

from relink.models import SearchQuery
from relink.network import PublicHTTPClient
from relink import workflow
from tests.test_datacite import record
from tests.pdf_fixtures import make_pdf


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in offline test'))
        guard.start()
        self.addCleanup(guard.stop)

    def test_multiline_form_context_is_normalized_for_the_existing_engine(self):
        query = workflow.query_from_input(' https://example.org/data.csv ', 'Forest measurements\nfrom a research\tpaper.')
        self.assertEqual(query.original_url, 'https://example.org/data.csv')
        self.assertEqual(query.description, 'Forest measurements from a research paper.')

    def test_doi_resolver_url_is_passed_to_repository_identity_search(self):
        query = workflow.query_from_input('https://doi.org/10.24432/C56C76')
        self.assertEqual(query.original_url, 'https://doi.org/10.24432/C56C76')
        self.assertEqual(query.doi, '10.24432/c56c76')

    def test_url_flow_checks_current_status_and_searches_each_provider_once(self):
        calls = []
        stages = []
        def handler(request):
            host = request.headers['host']
            calls.append(host)
            if host == 'archive.org':
                return httpx.Response(200, json={'archived_snapshots': {}})
            if host == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(404)
        with PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14']) as client:
            report = workflow.run_recovery(SearchQuery(original_url='https://example.org/data.csv'),
                                            client=client, on_progress=stages.append)
        self.assertEqual(report.current.http_status, 404)
        self.assertEqual(report.discovery.status, 'found')
        self.assertCountEqual(calls, ['example.org', 'archive.org', 'api.datacite.org'])
        self.assertEqual(len(stages), 2)
        payload = json.loads(workflow.report_json(report))
        self.assertEqual(payload['query']['original_url'], 'https://example.org/data.csv')
        self.assertEqual(payload['schema_version'], 1)

    def test_unsafe_dns_blocks_all_provider_calls(self):
        with PublicHTTPClient(transport=httpx.MockTransport(lambda r: self.fail('Unsafe request')),
                              resolver=lambda h, p: ['10.0.0.1']) as client:
            report = workflow.run_recovery(SearchQuery(original_url='https://example.org/data.csv'), client=client)
        self.assertEqual(report.current.status, 'blocked')
        self.assertEqual(report.discovery.status, 'error')
        self.assertEqual(report.discovery.candidates, ())

    def test_pdf_input_context_is_exported_without_pdf_bytes(self):
        with PublicHTTPClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            'data': [], 'archived_snapshots': {}})), resolver=lambda h, p: ['93.184.215.14']) as client:
            report = workflow.run_recovery(SearchQuery(original_url='https://example.org/data.csv'),
                input_context={'mode': 'pdf', 'filename': 'paper.pdf', 'selected_link_page': 1}, client=client)
        payload = json.loads(workflow.report_json(report))
        self.assertEqual(payload['input_context']['filename'], 'paper.pdf')
        self.assertNotIn('pdf_bytes', payload)

    @unittest.skipUnless(importlib.util.find_spec('pymupdf'), 'PyMuPDF is not installed')
    def test_real_pdf_link_runs_through_existing_engine_and_exports_evidence(self):
        from relink.extraction import extract_pdf_links
        extracted = extract_pdf_links(make_pdf())
        selected = extracted.links[0]
        def handler(request):
            if request.headers['host'] == 'archive.org':
                return httpx.Response(200, json={'archived_snapshots': {'closest': {
                    'available': True, 'status': '200', 'timestamp': '20200102030405',
                    'url': 'https://web.archive.org/web/20200102030405/https://example.org/data.csv'}}})
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(404)
        with PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14']) as client:
            report = workflow.run_recovery(SearchQuery(original_url=selected.url),
                input_context={'mode': 'pdf', 'selected_link_page': selected.occurrences[0].page}, client=client)
        exported = json.loads(workflow.report_json(report))
        self.assertEqual(len(exported['discovery']['candidates']), 2)
        self.assertEqual(exported['input_context']['selected_link_page'], 1)
        self.assertTrue(all(r['explanation'] for r in exported['discovery']['candidates']))

    def test_public_link_renderer_rejects_unsafe_schemes_and_addresses(self):
        for value in ['javascript:alert(1)', 'data:text/html,hello', 'http://127.0.0.1/',
                      'file:///tmp/x', 'https://user:pass@example.org/']:
            with self.subTest(value=value):
                self.assertIsNone(workflow.public_link(value))
        self.assertEqual(workflow.public_link('https://example.org/data.csv'), 'https://example.org/data.csv')
