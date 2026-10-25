"""Dataset search, cached combined results and space UI through native controls."""
from dataclasses import replace
from unittest.mock import patch

import httpx

from relink.gemini_config import GeminiSettings
from relink.network import PublicHTTPClient
from relink.workflow import run_recovery
from tests.test_app import AppTestBase, mock_report
from tests.test_datacite import record
from tests.test_dataset_ai import ai_response


class DatasetAppTests(AppTestBase):
    def test_topic_search_uses_combined_engine_once_and_renders_samples_safely(self):
        calls = []
        def handler(request):
            calls.append(request)
            if request.method == 'POST': return ai_response(request)
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(200, text='species,height\n<script>,1\noak,2\nfir,3\n', headers={'Content-Type': 'text/csv'})
        with PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14']) as client, patch(
            'relink.gemini_config.load_gemini_settings', return_value=GeminiSettings(api_key='mock-only')), patch(
            'relink.ui.run_recovery', side_effect=lambda query, **kw: run_recovery(query, client=client, **kw)):
            self.app.run()
            self.app.radio(key='input_mode').set_value('Search datasets').run()
            self.app.text_input(key='dataset_topic').set_value('forest soil measurements').run()
            self.recover_button().click().run()
            self.assertEqual(len(self.app.exception), 0)
            report = self.app.session_state['report']
            self.assertEqual(report.current.status, 'not_applicable')
            self.assertEqual(report.discovery.assessment.status, 'ranked')
            self.assertTrue(any('Combined' in t.value or 'Dataset AI' in t.value for t in self.app.caption))
            self.assertFalse(any('<script>' in m.value for m in self.app.markdown))
            count = len(calls)
            self.app.run()
            self.assertEqual(len(calls), count)
            self.app.text_input(key='dataset_topic').set_value('ocean observations').run()
            self.assertNotIn('report', self.app.session_state)

    def test_dataset_load_more_is_request_free(self):
        report = mock_report()
        row = report.discovery.candidates[0]
        rows = tuple(replace(row, candidate=replace(row.candidate, doi=f'10.1234/{i}', titles=(f'Candidate {i}',))) for i in range(25))
        report = replace(report, discovery=replace(report.discovery, candidates=rows))
        with patch('relink.ui.run_recovery', return_value=report) as search:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
            self.assertEqual(len([t for t in self.app.text if t.value.startswith('Candidate ')]), 10)
            self.app.button(key='dataset_load_more').click().run()
            self.assertEqual(len([t for t in self.app.text if t.value.startswith('Candidate ')]), 20)
            self.assertEqual(search.call_count, 1)

    def test_space_theme_and_real_controls_have_no_fake_initial_results(self):
        self.app.run()
        self.assertEqual(self.app.title[0].value, 'ReLink')
        self.assertTrue(any('Follow the signal' in m.value for m in self.app.markdown))
        self.assertFalse(self.app.session_state.get('report'))
        self.assertTrue(self.recover_button().disabled)

    def test_paper_actions_disclose_metadata_and_sample_processing_before_find(self):
        from tests.test_paper_app import paper_result
        with patch('relink.paper_ui.search_papers', return_value=paper_result()):
            self.app.run()
            self.app.text_area(key='paper_topic').set_value('forest measurements').run()
            self.app.button(key='find_papers').click().run()
        self.assertTrue(any('Google' in c.value and 'three rows' in c.value for c in self.app.tabs[1].caption))
