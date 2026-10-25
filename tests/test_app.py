"""Streamlit UI tests with mocked recovery and real local PDF input bytes."""

from dataclasses import replace
import importlib.util
import io
import json
import os
import socket
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx

from relink.models import (Candidate, CurrentStatus, DiscoveryResult, MatchStatus,
                           RankedCandidate, RankingEvidence, SearchQuery, SearchResult)
from relink.workflow import RecoveryReport
from relink.network import PublicHTTPClient
from tests.pdf_fixtures import make_pdf
from tests.test_datacite import record


APP = Path(__file__).resolve().parents[1] / 'app.py'
HAS_STREAMLIT = importlib.util.find_spec('streamlit') is not None
HAS_PYMUPDF = importlib.util.find_spec('pymupdf') is not None


def mock_report(query=None, *, status='found'):
    query = query or SearchQuery(original_url='https://example.org/data.csv')
    candidate = Candidate(source='datacite', doi='10.1234/fixture',
                           url='https://repo.example/data.csv', titles=('Mocked research measurements',))
    ranked = RankedCandidate(candidate, 10, MatchStatus.UNVERIFIED_CANDIDATE,
                              (RankingEvidence('filename', 10, 'Matching filename.', ('data.csv',), ('data.csv',)),))
    candidates = (ranked,) if status in ('found', 'partial') else ()
    provider_status = 'error' if status in ('partial', 'error') else 'found' if candidates else 'not_found'
    discovery = DiscoveryResult(status, candidates,
        (SearchResult(provider_status, 'datacite', (candidate,) if candidates else (), detail='Mocked service outcome.'),),
        'Metadata only; dataset identity unverified.')
    return RecoveryReport('2026-10-24T00:00:00+00:00', query,
                           CurrentStatus('not_found', query.original_url, 404), discovery)


class AppTestBase(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self.app = AppTest.from_file(str(APP), default_timeout=10)
        # AppTest otherwise reads real secrets when its secrets mapping is empty.
        self.app.secrets = {'TESTING': True}
        history_folder = tempfile.TemporaryDirectory()
        self.addCleanup(history_folder.cleanup)
        history_env = patch.dict(os.environ, {'RELINK_HISTORY_PATH': str(Path(history_folder.name) / 'history.json'),
                                              'RELINK_HISTORY_ENABLED': '1', 'RELINK_HISTORY_MODE': 'local'})
        history_env.start()
        self.addCleanup(history_env.stop)
        from relink.gemini_config import GeminiSettings
        gemini_config_guard = patch('relink.gemini_config.load_gemini_settings', return_value=GeminiSettings())
        gemini_config_guard.start()
        self.addCleanup(gemini_config_guard.stop)
        delay = patch('relink.providers.arxiv._fetch', side_effect=lambda client, url: client.fetch(url, read_body=True))
        delay.start()
        self.addCleanup(delay.stop)
        guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in UI test'))
        guard.start()
        self.addCleanup(guard.stop)

    def recover_button(self):
        return next(button for button in self.app.button if button.label == 'Find')


@unittest.skipUnless(HAS_STREAMLIT, 'Streamlit is not installed')
class AppTests(AppTestBase):
    def test_invalid_url_error_survives_rerun_and_clears_on_input_change(self):
        self.app.run()
        self.app.text_input(key='original_url').set_value('not a URL').run()
        self.recover_button().click().run()
        self.assertTrue(self.app.error)
        self.app.run()
        self.assertTrue(self.app.error)
        self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
        self.assertFalse(self.app.error)

    def test_url_only_find_needs_no_description_and_explains_single_result_and_export(self):
        with patch('relink.ui.run_recovery', return_value=mock_report()) as run:
            self.app.run()
            self.assertFalse(any(area.key == 'dataset_context' for area in self.app.text_area))
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertEqual(run.call_args.args[0].description, '')
        self.assertTrue(any('Only one candidate' in item.value for item in self.app.caption))
        self.assertTrue(any('machine-readable' in item.value for item in self.app.caption))

    def test_multiple_options_show_strongest_evidence_first_with_visible_reasons(self):
        from relink.ranking import rank_candidates
        query = SearchQuery(original_url='https://example.org/data.csv')
        weak = Candidate(source='datacite', doi='10.1234/weak', url='https://repo.example/unrelated',
                         titles=('Weak option',))
        strong = Candidate(source='datacite', doi='10.1234/strong', url=query.original_url,
                           titles=('Strong option',))
        ranked = tuple(rank_candidates(query, [weak, strong]))
        report = replace(mock_report(query), discovery=DiscoveryResult('found', ranked, (), 'Metadata only.'))
        with patch('relink.ui.run_recovery', return_value=report):
            self.app.run()
            self.app.text_input(key='original_url').set_value(query.original_url).run()
            self.recover_button().click().run()
        values = [item.value for item in self.app.text]
        self.assertLess(values.index('Strong option'), values.index('Weak option'))
        self.assertTrue(any('Matching original URL' in value for value in values))
        self.assertTrue(any('Best-ranked option' in item.value for item in self.app.subheader))
        self.assertTrue(any('Option 2' in item.value for item in self.app.subheader))

    def test_license_notice_and_configured_source_are_visible_without_requests(self):
        source = 'https://github.com/relink-team/relink'
        with patch.dict(os.environ, {'RELINK_SOURCE_URL': source}):
            self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any('AGPL-3.0-only' in item.value for item in self.app.caption))
        self.assertTrue(any('WITHOUT ANY WARRANTY' in item.value for item in self.app.text))
        self.assertTrue(any(link.proto.url == source for link in self.app.get('link_button')))

    def test_missing_or_unsafe_source_url_is_not_presented_as_available(self):
        for value in ('', 'javascript:alert(1)', 'http://127.0.0.1/private'):
            with self.subTest(value=value), patch.dict(os.environ, {'RELINK_SOURCE_URL': value}):
                self.app.run()
                self.assertTrue(any('Source code link is not configured' in item.value for item in self.app.warning))
                self.assertFalse(any(link.proto.label == 'Source code' for link in self.app.get('link_button')))

    def test_initial_view_has_two_modes_and_no_fake_results(self):
        self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.title[0].value, 'ReLink')
        self.assertEqual(self.app.radio[0].options, ['Recover URL', 'Analyze PDF'])
        self.assertTrue(self.recover_button().disabled)
        self.assertNotIn('report', self.app.session_state)

    def test_url_flow_calls_engine_once_and_persists_report_across_reruns(self):
        with patch('relink.ui.run_recovery', return_value=mock_report()) as run:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual(run.call_count, 1)
            report = self.app.session_state['report']
            self.assertEqual(report.discovery.candidates[0].candidate.source, 'datacite')
            self.assertTrue(self.app.get('download_button'))
            self.app.run()
            self.assertEqual(run.call_count, 1)
            self.assertEqual(self.app.session_state['report'], report)

    def test_changing_url_clears_stale_results_without_searching(self):
        with patch('relink.ui.run_recovery', return_value=mock_report()) as run:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
            self.app.text_input(key='original_url').set_value('https://example.org/another.csv').run()
            self.assertNotIn('report', self.app.session_state)
            self.assertEqual(run.call_count, 1)

    def test_invalid_url_is_surfaced_without_calling_engine(self):
        with patch('relink.ui.run_recovery') as run:
            self.app.run()
            self.app.text_input(key='original_url').set_value('http://localhost/private').run()
            self.recover_button().click().run()
            self.assertTrue(self.app.error)
            self.assertFalse(run.called)

    def test_partial_failure_and_no_results_are_visible(self):
        for status in ('partial', 'not_found', 'error'):
            with self.subTest(status=status), patch('relink.ui.run_recovery', return_value=mock_report(status=status)):
                self.app.run()
                self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
                self.recover_button().click().run()
                self.assertEqual(len(self.app.exception), 0)
                if status == 'partial':
                    self.assertTrue(self.app.warning)
                elif status == 'error':
                    self.assertTrue(self.app.error)
                else:
                    self.assertTrue(any('No candidates' in item.value for item in self.app.info))

    def test_unexpected_failure_does_not_leave_old_results_or_a_traceback(self):
        with patch('relink.ui.run_recovery', side_effect=RuntimeError('private traceback details')):
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertTrue(self.app.error)
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn('report', self.app.session_state)

    def test_remote_html_markdown_and_unsafe_links_stay_inert(self):
        malicious = '<script>alert(1)</script> ![track](https://evil.example/pixel)'
        report = mock_report()
        candidate = replace(report.discovery.candidates[0].candidate,
                             titles=(malicious,), url='javascript:alert(1)', evidence=(malicious,))
        report = replace(report, discovery=replace(report.discovery, candidates=(
            replace(report.discovery.candidates[0], candidate=candidate),)))
        with patch('relink.ui.run_recovery', return_value=report):
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any(malicious in item.value for item in self.app.text))
        self.assertFalse(any(malicious in item.value for item in self.app.markdown))
        for link in self.app.get('link_button'):
            self.assertFalse(link.proto.url.startswith('javascript:'))

    def test_json_export_contains_the_actual_report(self):
        import streamlit as st
        with patch('relink.ui.run_recovery', return_value=mock_report()), patch(
            'streamlit.download_button', wraps=st.download_button) as download:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        report_call = next(call for call in reversed(download.call_args_list)
                           if call.kwargs.get('file_name') == 'relink-recovery-report.json')
        payload = json.loads(report_call.kwargs['data'])
        self.assertEqual(payload['query']['original_url'], 'https://example.org/data.csv')
        self.assertEqual(payload['discovery']['candidates'][0]['candidate']['doi'], '10.1234/fixture')


@unittest.skipUnless(HAS_STREAMLIT and HAS_PYMUPDF, 'Streamlit and PyMuPDF are required')
class PDFAppTests(AppTestBase):
    def upload(self, content):
        # File upload is an external input boundary. Real PDF bytes are parsed by
        # the production extractor; only the widget's uploaded-file value is mocked.
        upload = io.BytesIO(content)
        upload.name = 'paper.pdf'
        return patch('streamlit.file_uploader', return_value=upload)

    def test_pdf_flow_extracts_selects_and_recovers_a_real_link(self):
        content = make_pdf('Measurements at https://example.org/data.csv')
        with self.upload(content), patch('relink.ui.run_recovery', side_effect=lambda q, **kw: replace(
            mock_report(q), input_context=kw.get('input_context', {}))) as run:
            self.app.run()
            self.app.radio[0].set_value('Analyze PDF').run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual(self.app.selectbox(key='pdf_link').value, 'https://example.org/data.csv')
            self.recover_button().click().run()
            self.assertEqual(run.call_count, 1)
            report = self.app.session_state['report']
            self.assertEqual(report.input_context['mode'], 'pdf')
            self.assertEqual(report.query.original_url, 'https://example.org/data.csv')
            self.assertEqual(len(self.app.exception), 0)

    def test_malformed_pdf_is_a_visible_error_and_cannot_recover(self):
        with self.upload(b'not a pdf'):
            self.app.run()
            self.app.radio[0].set_value('Analyze PDF').run()
        self.assertTrue(self.app.error)
        self.assertTrue(self.recover_button().disabled)
        self.assertEqual(len(self.app.exception), 0)

    def test_scanned_or_link_free_pdf_has_no_operational_recover_button(self):
        with self.upload(make_pdf('')):
            self.app.run()
            self.app.radio[0].set_value('Analyze PDF').run()
        self.assertTrue(self.app.warning)
        self.assertTrue(self.recover_button().disabled)


@unittest.skipUnless(HAS_STREAMLIT and HAS_PYMUPDF, 'Streamlit and PyMuPDF are required')
class EngineUIIntegrationTests(AppTestBase):
    """Native widgets and real engine modules; mock only external HTTP and DNS."""

    def setUp(self):
        super().setUp()
        self.requests = []
        factory = patch('relink.workflow.PublicHTTPClient', side_effect=self.make_client)
        factory.start()
        self.addCleanup(factory.stop)

    def make_client(self):
        def handler(request):
            self.requests.append(request)
            if request.headers['host'] == 'archive.org':
                return httpx.Response(200, json={'archived_snapshots': {'closest': {
                    'available': True, 'status': '200', 'timestamp': '20200102030405',
                    'url': 'https://web.archive.org/web/20200102030405/https://example.org/data.csv'}}})
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(404)
        return PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])

    def test_url_widgets_run_existing_engine_and_export_without_repeating_requests(self):
        self.app.run()
        self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
        self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.requests), 3)
        report = self.app.session_state['report']
        self.assertEqual(report.current.http_status, 404)
        self.assertEqual({r.candidate.source for r in report.discovery.candidates}, {'datacite', 'internet_archive'})
        self.assertTrue(all(r.status != 'verified_exact_match' for r in report.discovery.candidates))
        self.app.download_button[0].click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.requests), 3)

    def test_native_pdf_upload_select_recover_and_remove_clears_report(self):
        self.app.run()
        self.app.radio[0].set_value('Analyze PDF').run()
        self.app.file_uploader[0].set_value(('paper.pdf', make_pdf(), 'application/pdf')).run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.selectbox(key='pdf_link').value, 'https://example.org/data.csv')
        self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.requests), 3)
        report = self.app.session_state['report']
        self.assertEqual(report.input_context['filename'], 'paper.pdf')
        self.assertEqual(report.input_context['occurrences'][0]['page'], 1)
        self.assertEqual(len(report.discovery.candidates), 2)
        self.app.file_uploader[0].clear().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn('report', self.app.session_state)
        self.assertTrue(self.recover_button().disabled)
        self.assertEqual(len(self.requests), 3)

    def test_changing_selected_pdf_link_clears_previous_results(self):
        self.app.run()
        self.app.radio[0].set_value('Analyze PDF').run()
        content = make_pdf('https://example.org/data.csv https://example.org/other.csv')
        self.app.file_uploader[0].set_value(('paper.pdf', content, 'application/pdf')).run()
        self.recover_button().click().run()
        self.assertIn('report', self.app.session_state)
        self.app.selectbox(key='pdf_link').set_value('https://example.org/other.csv').run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn('report', self.app.session_state)
        self.assertEqual(len(self.requests), 3)

    def test_doi_url_redirects_and_repository_identity_search_work_together(self):
        requests = []
        def handler(request):
            requests.append(request)
            host = request.headers['host']
            if host == 'doi.org':
                return httpx.Response(302, headers={'Location': 'https://archive.ics.uci.edu/dataset/53/iris'})
            if host == 'archive.org':
                return httpx.Response(200, json={'archived_snapshots': {}})
            if host == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record('10.24432/C56C76',
                    titles=[{'title': 'Iris'}], url='https://archive.ics.uci.edu/dataset/53/iris')], 'meta': {'total': 1}})
            return httpx.Response(200)
        def client_factory():
            return PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        with patch('relink.workflow.PublicHTTPClient', side_effect=client_factory):
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://doi.org/10.24432/C56C76').run()
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        report = self.app.session_state['report']
        self.assertEqual(report.query.doi, '10.24432/c56c76')
        self.assertEqual(report.current.status, 'working')
        self.assertEqual(report.discovery.status, 'found')
        self.assertEqual(report.discovery.candidates[0].status, 'likely_match')
        datacite = next(request for request in requests if request.headers['host'] == 'api.datacite.org')
        self.assertNotIn('url:', datacite.url.params['query'])

    def test_dns_failures_do_not_display_sample_candidates(self):
        def resolve(host, port):
            raise socket.gaierror(socket.EAI_NONAME, 'offline fixture')
        def client_factory():
            return PublicHTTPClient(transport=httpx.MockTransport(lambda r: self.fail('HTTP after DNS failure')),
                                    resolver=resolve)
        with patch('relink.workflow.PublicHTTPClient', side_effect=client_factory):
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        report = self.app.session_state['report']
        self.assertEqual(report.discovery.candidates, ())
        self.assertTrue(all(p.status == 'dns_failure' for p in report.discovery.providers))
        self.assertFalse(any(h.value.startswith('Candidate ') for h in self.app.subheader))
        self.assertTrue(self.app.error)
