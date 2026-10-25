"""Two-tab paper workflow tests with explicit mocked remote boundaries."""
from dataclasses import replace
from unittest.mock import patch

from relink.extraction import ExtractedLink, LinkOccurrence
import httpx

from relink.models import SearchResult
from relink.network import PublicHTTPClient
from relink.paper_models import Paper, PaperDatasetLookup, PaperSearchResult, RankedPaper
from tests.test_app import AppTestBase, mock_report
from tests.test_papers import work
from tests.pdf_fixtures import make_pdf


def paper_result():
    paper = Paper('https://openalex.org/W1', 'Forest observations', 'Forest climate data',
                  doi='10.1234/paper', pdf_url='https://example.org/paper.pdf')
    ranked = RankedPaper(paper, 20, ('forest', 'climate'), ('forest', 'climate'))
    return PaperSearchResult('found', (ranked,), retrieved_count=1)


class PaperAppTests(AppTestBase):
    def test_action_errors_persist_without_repeating_failed_requests(self):
        with patch('relink.paper_ui.search_papers', return_value=paper_result()), patch(
            'relink.paper_ui.lookup_paper_datasets', side_effect=RuntimeError('mock failure')) as lookup:
            self.search()
            self.app.button(key='lookup_paper_datasets').click().run()
            self.assertTrue(self.app.error)
            self.app.run()
            self.assertTrue(self.app.error)
            self.assertEqual(lookup.call_count, 1)
            self.app.text_area(key='paper_topic').set_value('new topic').run()
            self.assertFalse(self.app.error)

    def test_topic_validation_error_persists_and_long_abstract_has_a_preview(self):
        with patch('relink.paper_ui.search_papers', side_effect=ValueError('Include a keyword')) as search:
            self.search()
            self.app.run()
            self.assertTrue(self.app.error)
            self.assertTrue(any('Include a keyword' in item.value for item in self.app.text))
            self.assertEqual(search.call_count, 1)
        result = paper_result()
        long_abstract = 'forest climate ' * 200
        result = replace(result, papers=(replace(result.papers[0], paper=replace(
            result.papers[0].paper, abstract=long_abstract)),))
        with patch('relink.paper_ui.search_papers', return_value=result):
            self.app.button(key='find_papers').click().run()
        self.assertTrue(any(item.label == 'Read full abstract' for item in self.app.expander))
        self.assertTrue(any(0 < len(item.value) < len(long_abstract) and item.value.endswith('…') for item in self.app.text))

    def search(self):
        self.app.run()
        self.app.text_area(key='paper_topic').set_value('forest climate').run()
        self.app.button(key='find_papers').click().run()

    def test_two_tabs_paper_search_abstract_and_request_free_reruns(self):
        with patch('relink.paper_ui.search_papers', return_value=paper_result()) as search:
            self.search()
            self.assertEqual([tab.label for tab in self.app.tabs], ['Find datasets', 'Find papers'])
            self.assertEqual(search.call_count, 1)
            self.assertTrue(any('Forest climate data' in item.value for item in self.app.text))
            self.app.run()
            self.assertEqual(search.call_count, 1)
            self.app.text_area(key='paper_topic').set_value('ocean').run()
            self.assertNotIn('paper_search_result', self.app.session_state)
            self.assertFalse(self.app.button(key='lookup_paper_datasets').value if any(
                b.key == 'lookup_paper_datasets' for b in self.app.button) else False)

    def test_paper_to_dataset_link_to_existing_recovery_engine(self):
        lookup = PaperDatasetLookup('https://openalex.org/W1', SearchResult('not_found', 'datacite'),
            (ExtractedLink('https://example.org/data.csv', (LinkOccurrence(1, 'Dataset context', 'text'),)),),
            'extracted', 'Parsed a real local fixture PDF.')
        with patch('relink.paper_ui.search_papers', return_value=paper_result()), patch(
            'relink.paper_ui.lookup_paper_datasets', return_value=lookup) as find, patch(
            'relink.paper_ui.run_recovery', return_value=mock_report()) as recover:
            self.search()
            self.app.button(key='lookup_paper_datasets').click().run()
            self.app.button(key='recover_paper_link').click().run()
            self.assertEqual(find.call_count, 1)
            self.assertEqual(recover.call_count, 1)
            self.assertEqual(recover.call_args.args[0].original_url, 'https://example.org/data.csv')
            self.assertEqual(len(self.app.exception), 0)
            self.app.run()
            self.assertEqual(find.call_count, 1)
            self.assertEqual(recover.call_count, 1)

    def test_paper_errors_and_remote_markup_remain_visible_and_inert(self):
        result = paper_result()
        malicious = '<script>alert(1)</script>'
        result = replace(result, papers=(replace(result.papers[0], paper=replace(
            result.papers[0].paper, title=malicious, abstract=malicious, landing_url='javascript:alert(1)')),))
        with patch('relink.paper_ui.search_papers', return_value=result):
            self.search()
        self.assertTrue(any(malicious in item.value for item in self.app.text))
        self.assertFalse(any(malicious in item.value for item in self.app.markdown))
        self.assertFalse(any(link.proto.url.startswith('javascript:') for link in self.app.get('link_button')))
        with patch('relink.paper_ui.search_papers', return_value=PaperSearchResult(
            'rate_limited', detail='Mock rate limit', retry_after='30')):
            self.app.button(key='find_papers').click().run()
        self.assertTrue(any('Mock rate limit' in item.value for item in self.app.text))
        self.assertNotIn('paper_lookup_result', self.app.session_state)

    def test_native_flow_runs_real_modules_with_mock_http_and_keeps_both_reports(self):
        from relink.papers import lookup_paper_datasets, search_papers
        from relink.workflow import run_recovery
        requests = []
        def handler(request):
            requests.append(request)
            host = request.headers['host']
            if host == 'api.openalex.org':
                return httpx.Response(200, json={'results': [work(abstract='forest climate')]})
            if host == 'api.datacite.org':
                return httpx.Response(200, json={'data': [], 'meta': {'total': 0}})
            if host == 'archive.org':
                return httpx.Response(200, json={'archived_snapshots': {'closest': {
                    'available': True, 'status': '200', 'timestamp': '20200102030405',
                    'url': 'https://web.archive.org/web/20200102030405/https://example.org/data.csv'}}})
            if request.url.path == '/paper.pdf':
                return httpx.Response(200, content=make_pdf('Dataset https://example.org/data.csv'))
            return httpx.Response(404)
        with PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14']) as client, patch(
            'relink.paper_ui.search_papers', side_effect=lambda topic: search_papers(topic, client=client)), patch(
            'relink.paper_ui.lookup_paper_datasets', side_effect=lambda paper, **kwargs: lookup_paper_datasets(paper, client=client, **kwargs)), patch(
            'relink.paper_ui.run_recovery', side_effect=lambda query, **kwargs: run_recovery(query, client=client, **kwargs)):
            self.search()
            self.app.button(key='lookup_paper_datasets').click().run()
            self.app.button(key='recover_paper_link').click().run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual(self.app.session_state['paper_link_report'].discovery.status, 'found')
            # Identical URLs/cards in both tabs must not collide as Streamlit widgets.
            self.app.session_state['report'] = mock_report()
            self.app.run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual(len([button for button in self.app.download_button
                                  if button.key in ('dataset_report_download', 'paper_report_download')]), 2)
            request_count = len(requests)
            self.app.run()
            self.assertEqual(len(requests), request_count)

    def test_changing_selected_paper_clears_dataset_lookup_and_recovery(self):
        result = paper_result()
        other = replace(result.papers[0], paper=replace(result.papers[0].paper, id='https://openalex.org/W2', title='Second paper'))
        result = replace(result, papers=result.papers + (other,))
        lookup = PaperDatasetLookup(result.papers[0].paper.id, SearchResult('not_found', 'datacite'))
        with patch('relink.paper_ui.search_papers', return_value=result), patch(
            'relink.paper_ui.lookup_paper_datasets', return_value=lookup) as find:
            self.search()
            self.app.button(key='lookup_paper_datasets').click().run()
            self.assertIn('paper_lookup_result', self.app.session_state)
            self.app.selectbox(key='paper_choice').set_value('https://openalex.org/W2').run()
            self.assertNotIn('paper_lookup_result', self.app.session_state)
            self.assertNotIn('paper_link_report', self.app.session_state)
            self.assertEqual(find.call_count, 1)
