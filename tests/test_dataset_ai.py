"""Combined dataset relevance uses only actual returned metadata/sample evidence."""
from dataclasses import replace
import json
import unittest

import httpx

from relink.gemini_config import GeminiSettings
from relink.models import Candidate, MatchStatus, SearchQuery, RankingEvidence
from relink.network import PublicHTTPClient
from relink.ranking import rank_candidates


def ai_response(request, *, invalid=False):
    supplied = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['datasets']
    rows = [{'id': row['id'], 'evidence_id': row['evidence'][0]['id'],
             'reason': 'The returned metadata describes the requested measurements.'} for row in reversed(supplied)]
    if invalid: rows[0]['evidence_id'] = 99999
    return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP',
        'content': {'parts': [{'text': json.dumps({'ranking': rows})}]}}]})


class DatasetAITests(unittest.TestCase):
    def client(self, handler):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def candidates(self):
        return [Candidate(source='datacite', doi='10.1234/' + str(i), url=f'https://example.org/{i}.csv',
                          titles=(f'Forest measurements {i}',), descriptions=('Forest climate observations.',)) for i in range(5)]

    def test_metadata_and_three_row_samples_are_ranked_once_without_changing_verification(self):
        from relink.dataset_ai import assess_datasets
        calls = []
        def handler(request):
            calls.append(request)
            if request.method == 'POST': return ai_response(request)
            return httpx.Response(200, text='species,height\npine,1\noak,2\nfir,3\nDO_NOT_SEND,4\n',
                                  headers={'Content-Type': 'text/csv'})
        query = SearchQuery(description='forest climate measurements')
        original = tuple(rank_candidates(query, self.candidates()))
        ordered, assessment = assess_datasets(query, original, client=self.client(handler), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(assessment.status, 'ranked')
        self.assertEqual(len(assessment.previews), 3)
        self.assertEqual(len([r for r in calls if r.method == 'POST']), 1)
        self.assertEqual(len([r for r in calls if r.method == 'GET']), 3)
        self.assertTrue(all(len(p.rows) == 3 for p in assessment.previews))
        posted = next(r.content.decode() for r in calls if r.method == 'POST')
        self.assertNotIn('DO_NOT_SEND', posted)
        self.assertNotIn('mock-only', posted)
        self.assertEqual(ordered[0].candidate.doi, original[-1].candidate.doi)
        self.assertTrue(all(r.ai_reason and r.ai_evidence for r in ordered))
        self.assertEqual({r.candidate.doi: (r.score, r.status) for r in ordered},
                         {r.candidate.doi: (r.score, r.status) for r in original})

    def test_identity_and_conflict_tiers_override_model_preference(self):
        from relink.dataset_ai import assess_datasets
        query = SearchQuery(doi='10.1234/0', description='forest')
        ranked = list(rank_candidates(query, self.candidates()))
        ranked[0] = replace(ranked[0], status=MatchStatus.VERIFIED_EXACT_MATCH)
        ranked[-1] = replace(ranked[-1], status=MatchStatus.DIFFERENT_VERSION)
        def handler(request):
            return ai_response(request) if request.method == 'POST' else httpx.Response(404)
        ordered, assessment = assess_datasets(query, tuple(ranked), client=self.client(handler), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(assessment.status, 'ranked')
        self.assertEqual(ordered[0].status, MatchStatus.VERIFIED_EXACT_MATCH)
        self.assertEqual(ordered[-1].status, MatchStatus.DIFFERENT_VERSION)

    def test_bad_evidence_quota_timeout_and_missing_key_preserve_existing_order(self):
        from relink.dataset_ai import assess_datasets
        original = tuple(rank_candidates(SearchQuery(title='forest'), self.candidates()[:2]))
        for outcome in ('invalid', 'quota', 'timeout', 'missing'):
            calls = []
            def handler(request):
                calls.append(request)
                if request.method != 'POST': return httpx.Response(404)
                if outcome == 'timeout': raise httpx.ReadTimeout('mock-only', request=request)
                if outcome == 'quota': return httpx.Response(429, headers={'Retry-After': '60'})
                return ai_response(request, invalid=True)
            with self.subTest(outcome=outcome):
                ordered, assessment = assess_datasets(SearchQuery(title='forest'), original,
                    client=self.client(handler), settings=GeminiSettings(api_key='' if outcome == 'missing' else 'mock-only'))
                self.assertEqual(ordered, original)
                self.assertEqual(assessment.status, {'invalid': 'invalid_response', 'quota': 'rate_limited',
                    'timeout': 'timeout', 'missing': 'not_configured'}[outcome])
                if outcome == 'missing': self.assertFalse(calls)
                self.assertNotIn('mock-only', assessment.detail)

    def test_empty_candidates_do_not_call_model(self):
        from relink.dataset_ai import assess_datasets
        ordered, assessment = assess_datasets(SearchQuery(title='forest'), (),
            client=self.client(lambda r: self.fail('No request expected')), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(assessment.status, 'not_found')
        self.assertFalse(ordered)

    def test_candidates_beyond_model_cap_are_retained_with_an_explicit_limit(self):
        from relink.dataset_ai import assess_datasets
        candidates = [Candidate(source='datacite', doi=f'10.1234/{i}', titles=(f'Forest {i}',)) for i in range(35)]
        query = SearchQuery(description='forest observations')
        original = tuple(rank_candidates(query, candidates))
        def handler(request):
            rows = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['datasets']
            self.assertEqual(len(rows), 30)
            return ai_response(request)
        ordered, assessment = assess_datasets(query, original, client=self.client(handler), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(len(ordered), 35)
        self.assertTrue(assessment.warnings)
        self.assertEqual(sum(bool(r.ai_reason) for r in ordered), 30)

    def test_unknown_duplicate_missing_ids_and_extra_fields_never_create_evidence(self):
        from relink.dataset_ai import assess_datasets
        original = tuple(rank_candidates(SearchQuery(title='forest'), self.candidates()[:2]))
        for mutation in ('unknown', 'duplicate', 'missing', 'extra', 'bool', 'unfinished', 'json'):
            def handler(request):
                if request.method != 'POST': return httpx.Response(404)
                body = json.loads(ai_response(request).content)
                rows = json.loads(body['candidates'][0]['content']['parts'][0]['text'])['ranking']
                if mutation == 'unknown': rows[0]['id'] = 'invented'
                if mutation == 'duplicate': rows[0]['id'] = rows[1]['id']
                if mutation == 'missing': rows.pop()
                if mutation == 'extra': rows[0]['url'] = 'https://fabricated.example/'
                if mutation == 'bool': rows[0]['evidence_id'] = True
                if mutation == 'unfinished': body['candidates'][0]['finishReason'] = 'MAX_TOKENS'
                if mutation == 'json': return httpx.Response(200, text='bad JSON')
                body['candidates'][0]['content']['parts'][0]['text'] = json.dumps({'ranking': rows})
                return httpx.Response(200, json=body)
            with self.subTest(mutation=mutation):
                ordered, assessment = assess_datasets(SearchQuery(title='forest'), original,
                    client=self.client(handler), settings=GeminiSettings(api_key='mock-only'))
                self.assertEqual(ordered, original)
                self.assertEqual(assessment.status, 'invalid_response')

    def test_combining_paper_results_preserves_original_identity_and_hash_evidence(self):
        from relink.dataset_ai import combine_dataset_results
        from relink.models import DiscoveryResult, HashEvidence
        original = Candidate(source='internet_archive', original_url='https://example.org/data.csv',
                             archived_url='https://web.archive.org/web/20200101000000/https://example.org/data.csv')
        query = SearchQuery(original_url=original.original_url)
        for evidence in ((), (HashEvidence(original.archived_url, 'a' * 64, 'a' * 64, 'trusted reference', 'independent candidate'),)):
            initial_rows = tuple(rank_candidates(query, [original], hash_evidence=evidence))
            initial = DiscoveryResult('found', initial_rows, (), 'Actual earlier URL evidence.')
            combined = combine_dataset_results(SearchQuery(description='Datasets in a paper'), (), initial=initial,
                settings=GeminiSettings(), client=self.client(lambda r: self.fail('No request expected')))
            self.assertEqual(combined.candidates[0].status, initial_rows[0].status)
            self.assertEqual(combined.candidates[0].score, initial_rows[0].score)
            self.assertEqual(combined.candidates[0].explanation, initial_rows[0].explanation)

    def test_actual_named_version_warning_survives_combining_and_ai_preference(self):
        from relink.dataset_ai import combine_dataset_results
        from relink.gemini import identify_and_discover
        from tests.test_gemini import PAGES, mention, response
        from tests.test_datacite import record
        def handler(request):
            if request.method == 'POST':
                data = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])
                return ai_response(request) if 'datasets' in data else httpx.Response(200, json=response([mention()]))
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record('10.1234/correct', titles=[{'title': 'SQuAD'}], version='1.1'),
                    record('10.1234/wrong', titles=[{'title': 'SQuAD'}], version='2.0')], 'meta': {'total': 2}})
            return httpx.Response(404)
        client, settings = self.client(handler), GeminiSettings(api_key='mock-only')
        _, groups = identify_and_discover(PAGES, settings=settings, client=client)
        combined = combine_dataset_results(SearchQuery(description='SQuAD dataset'), tuple(g.result for g in groups),
            settings=settings, client=client, prior_ranked=tuple(r for g in groups for r in g.ranked))
        self.assertEqual(combined.assessment.status, 'ranked')
        self.assertEqual(combined.candidates[0].candidate.version, '1.1')
        self.assertEqual(combined.candidates[-1].candidate.version, '2.0')
        self.assertTrue(any(e.signal == 'requested_version' for e in combined.candidates[-1].explanation))
