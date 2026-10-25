"""Dataset topic/URL and paper handoff use one combined real-engine assessment."""
import json
import unittest
import tempfile
from pathlib import Path

import httpx

from relink.gemini_config import GeminiSettings
from relink.models import SearchQuery
from relink.network import PublicHTTPClient
from relink.paper_models import Paper
from relink.papers import lookup_paper_datasets
from relink.workflow import run_recovery
from tests.test_datacite import record
from tests.test_dataset_ai import ai_response


class DatasetWorkflowTests(unittest.TestCase):
    def client(self, calls):
        def handler(request):
            calls.append(request)
            if request.headers['host'] == 'generativelanguage.googleapis.com':
                data = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])
                if 'datasets' in data: return ai_response(request)
                return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP', 'content': {'parts': [
                    {'text': json.dumps({'datasets': [{'name': 'ForestData', 'version': '', 'page': 0,
                                                       'quote': 'We use ForestData measurements.'}]})}]}}]})
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            if request.headers['host'] == 'archive.org': return httpx.Response(200, json={'archived_snapshots': {}})
            return httpx.Response(200, text='species,height\npine,1\noak,2\nfir,3\n', headers={'Content-Type': 'text/csv'})
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def test_topic_search_has_no_fabricated_original_url_and_combines_ai(self):
        calls = []
        report = run_recovery(SearchQuery(description='forest measurements'), client=self.client(calls),
                              settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(report.current.status, 'not_applicable')
        self.assertFalse(report.query.original_url)
        self.assertEqual(report.discovery.assessment.status, 'ranked')
        self.assertTrue(report.discovery.candidates[0].ai_reason)
        self.assertFalse(any(r.headers['host'] == 'archive.org' for r in calls))

    def test_url_recovery_preserves_provider_outcomes_and_assesses_returned_records(self):
        calls = []
        report = run_recovery(SearchQuery(original_url='https://example.org/input.csv'), client=self.client(calls),
                              settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(report.current.status, 'working')
        self.assertEqual(len(report.discovery.providers), 2)
        self.assertEqual(report.discovery.assessment.status, 'ranked')
        self.assertEqual(len([r for r in calls if r.method == 'POST']), 1)

    def test_selected_paper_merges_named_and_related_records_in_one_assessment(self):
        calls = []
        paper = Paper('https://openalex.org/W1', 'Forest paper', 'We use ForestData measurements.', doi='10.1234/paper')
        lookup = lookup_paper_datasets(paper, client=self.client(calls), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(lookup.combined.assessment.status, 'ranked')
        self.assertEqual(len(lookup.combined.candidates), 1)
        self.assertEqual(len([r for r in calls if r.method == 'POST']), 2)  # Identify once, assess combined batch once.

    def test_assessment_and_sample_history_round_trip_without_credentials(self):
        from relink.history import HistoryStore, restore_snapshot
        report = run_recovery(SearchQuery(description='forest measurements'), client=self.client([]),
                              settings=GeminiSettings(api_key='mock-only'))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'history.json'
            entry = HistoryStore(path).add('recovery', 'forest measurements', report)
            self.assertEqual(restore_snapshot(entry), report)
            self.assertNotIn('mock-only', path.read_text())

    def test_uploaded_pdf_handoff_retains_prior_independent_hash_and_url_checks(self):
        from relink.extraction import extract_pdf_links
        from relink.models import Candidate, DiscoveryResult, HashEvidence, MatchStatus
        from relink.papers import lookup_uploaded_datasets
        from relink.ranking import rank_candidates
        from tests.pdf_fixtures import make_pdf
        url = 'https://example.org/data.csv'
        candidate = Candidate(source='datacite', url=url, doi='10.1234/data')
        ranked = tuple(rank_candidates(SearchQuery(original_url=url), [candidate],
            hash_evidence=(HashEvidence(url, 'a' * 64, 'a' * 64, 'trusted reference', 'independent candidate'),)))
        initial = DiscoveryResult('found', ranked, (), 'Independent checks already completed.')
        extracted = extract_pdf_links(make_pdf('Dataset ' + url))
        lookup = lookup_uploaded_datasets(extracted, paper_id='uploaded-pdf:fixture', settings=GeminiSettings(),
                                         client=self.client([]), initial=initial)
        result = lookup.combined.candidates[0]
        self.assertEqual(result.status, MatchStatus.VERIFIED_EXACT_MATCH)
        self.assertEqual(result.score, ranked[0].score)
        self.assertEqual(result.explanation, ranked[0].explanation)
