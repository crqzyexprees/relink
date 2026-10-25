"""Offline multi-source retrieval and Gemini reranking: no live credentials/DNS."""
from dataclasses import asdict, replace
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock
from unittest.mock import patch
from xml.sax.saxutils import escape

import httpx

from relink.gemini_config import GeminiSettings
from relink.paper_models import Paper
from relink.network import PublicHTTPClient
from relink.papers import search_papers
from relink.providers.arxiv import _fetch as fetch_arxiv
from tests import test_papers as paper_helpers
from tests.test_papers import work


def feed(count=1, *, start=0, doi='', abstract='forest climate observations'):
    entries = ''.join(f'''<entry><id>http://arxiv.org/abs/2401.{index:05d}v1</id>
        <title>Preprint {index}</title><summary>{escape(abstract)}</summary>
        <published>2024-01-02T00:00:00Z</published><author><name>A. Author</name></author>
        <arxiv:doi>{escape(doi)}</arxiv:doi>
        <link title="pdf" type="application/pdf" href="http://arxiv.org/pdf/2401.{index:05d}v1"/>
        </entry>''' for index in range(start, start + count))
    return f'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">{entries}</feed>'


def model_response(rows):
    return httpx.Response(200, json={'candidates': [{'finishReason': 'STOP',
        'content': {'parts': [{'text': json.dumps({'ranking': rows})}]}}]})


def ranking_rows(request):
    supplied = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['papers']
    return [{'id': row['id'], 'quote': ' '.join(row['abstract'].split()[:5]),
             'reason': 'Discusses the requested subject in the supplied abstract.'} for row in reversed(supplied)]


class PaperRankingTests(unittest.TestCase):
    """Use the existing HTTP/DNS guards without repeating inherited test cases."""
    setUp = paper_helpers.PaperTests.setUp

    def client(self, handler):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def search_handler(self, *, count=15, model=None, requests=None):
        def handler(request):
            if requests is not None: requests.append(request)
            host = request.headers['host']
            if host == 'api.openalex.org':
                return httpx.Response(200, json={'results': [work('W' + str(i)) for i in range(count)]})
            if host == 'export.arxiv.org': return httpx.Response(200, text=feed(count))
            if host == 'generativelanguage.googleapis.com':
                return model(request) if model else model_response(ranking_rows(request))
            self.fail('Unexpected HTTP target: ' + host)
        return handler

    def test_retrieves_thirty_before_ranking_and_preserves_all_model_ordered_papers(self):
        requests = []
        with patch('relink.providers.arxiv.time.sleep'):
            result = search_papers('forest climate', client=self.client(self.search_handler(requests=requests)),
                                   settings=GeminiSettings(api_key='mock-secret'))
        self.assertEqual(len(result.papers), 30)
        self.assertEqual(result.ranking.status, 'ranked')
        self.assertEqual([row.semantic_rank for row in result.papers], list(range(1, 31)))
        self.assertEqual(result.papers[0].paper.source, 'arxiv')
        self.assertTrue(all(row.semantic_evidence for row in result.papers))
        model_requests = [r for r in requests if r.method == 'POST']
        self.assertEqual(len(model_requests), 1)
        posted = json.loads(json.loads(model_requests[0].content)['contents'][0]['parts'][0]['text'])
        self.assertEqual(len(posted['papers']), 30)
        self.assertNotIn('title', posted['papers'][0])
        self.assertEqual(model_requests[0].headers['x-goog-api-key'], 'mock-secret')
        self.assertNotIn('mock-secret', str(asdict(result)))
        self.assertTrue(all(row.paper.provenance for row in result.papers))

    def test_cross_source_dedup_retains_provenance_pdf_and_does_not_merge_conflicting_dois(self):
        first = work('W1'); first['doi'] = 'https://doi.org/10.1234/shared'
        first['best_oa_location'] = {}; first['primary_location'] = {}
        def handler(request):
            if request.headers['host'] == 'api.openalex.org':
                return httpx.Response(200, json={'results': [first]})
            return httpx.Response(200, text=feed(1, doi='10.1234/shared'))
        with patch('relink.providers.arxiv.time.sleep'):
            result = search_papers('forest climate', client=self.client(handler))
        self.assertEqual(len(result.papers), 1)
        paper = result.papers[0].paper
        self.assertEqual({p.source for p in paper.provenance}, {'openalex', 'arxiv'})
        self.assertIn('arxiv.org/pdf/', paper.pdf_url)
        from relink.paper_ranking import deduplicate_papers
        conflicting = replace(paper, id='https://openalex.org/W2', doi='10.1234/other')
        self.assertEqual(len(deduplicate_papers((paper, conflicting), ('forest',))), 2)

    def test_unknown_duplicate_omitted_ids_and_invented_quotes_fall_back_without_accepting_evidence(self):
        for mutation in ('unknown', 'duplicate', 'omitted', 'quote', 'extra', 'truncated'):
            def invalid(request):
                rows = ranking_rows(request)
                if mutation == 'unknown': rows[0]['id'] = 'fabricated'
                if mutation == 'duplicate': rows[0]['id'] = rows[1]['id']
                if mutation == 'omitted': rows.pop()
                if mutation == 'quote': rows[0]['quote'] = 'invented supporting evidence'
                if mutation == 'extra': rows[0]['url'] = 'https://invented.example'
                if mutation == 'truncated': return httpx.Response(200, json={'candidates': [{'finishReason': 'MAX_TOKENS'}]})
                return model_response(rows)
            with self.subTest(mutation=mutation), patch('relink.providers.arxiv.time.sleep'):
                result = search_papers('forest climate', client=self.client(self.search_handler(count=1, model=invalid)),
                                       settings=GeminiSettings(api_key='mock-secret'))
                self.assertEqual(result.ranking.status, 'invalid_response')
                self.assertEqual(len(result.papers), 2)
                self.assertTrue(all(row.semantic_rank is None and not row.semantic_evidence for row in result.papers))

    def test_model_quota_timeout_and_missing_key_keep_honest_keyword_results(self):
        for code, expected in ((429, 'rate_limited'), (403, 'authentication_error'), (503, 'error')):
            with self.subTest(code=code), patch('relink.providers.arxiv.time.sleep'):
                result = search_papers('forest', client=self.client(self.search_handler(count=1,
                    model=lambda r: httpx.Response(code, headers={'Retry-After': '45'}, text='mock-secret'))),
                    settings=GeminiSettings(api_key='mock-secret'))
                self.assertEqual(result.ranking.status, expected)
                self.assertTrue(result.papers)
                self.assertNotIn('mock-secret', str(asdict(result)))
                if code == 429: self.assertEqual(result.ranking.retry_after, '45')
        def timeout(request): raise httpx.ReadTimeout('mock-secret', request=request)
        with patch('relink.providers.arxiv.time.sleep'):
            result = search_papers('forest', client=self.client(self.search_handler(count=1, model=timeout)),
                                   settings=GeminiSettings(api_key='mock-secret'))
            self.assertEqual(result.ranking.status, 'timeout')
            requests = []
            result = search_papers('forest', client=self.client(self.search_handler(count=1, requests=requests)))
            self.assertEqual(result.ranking.status, 'not_configured')
            self.assertFalse(any(r.method == 'POST' for r in requests))

    def test_one_source_failure_does_not_discard_other_source_or_claim_complete_search(self):
        for failing_host in ('api.openalex.org', 'export.arxiv.org'):
            original = self.search_handler(count=1)
            def handler(request):
                return httpx.Response(429, headers={'Retry-After': '30'}) if request.headers['host'] == failing_host else original(request)
            with self.subTest(host=failing_host), patch('relink.providers.arxiv.time.sleep'):
                result = search_papers('forest', client=self.client(handler))
                self.assertEqual(result.status, 'partial')
                self.assertEqual(len(result.papers), 1)
                self.assertEqual(len(result.providers), 2)
                self.assertTrue(any(p.status == 'rate_limited' and p.retry_after == '30' for p in result.providers))

    def test_next_batch_uses_application_paging_excludes_prior_ids_and_caps_batches(self):
        requests = []
        with patch('relink.providers.arxiv.time.sleep'):
            first = search_papers('forest', client=self.client(self.search_handler(requests=requests)))
            second = search_papers('forest', client=self.client(self.search_handler(requests=requests)), batch=1,
                                   exclude_identifiers=first.seen_identifiers)
        self.assertEqual(first.batch, 0)
        self.assertTrue(first.has_more)
        self.assertFalse(second.papers)
        self.assertEqual(second.status, 'not_found')
        self.assertEqual(requests[2].url.params['page'], '2')
        self.assertEqual(requests[3].url.params['start'], '15')
        with self.assertRaises(ValueError):
            search_papers('forest', client=self.client(lambda r: self.fail('No request expected')), batch=3)

    def test_arxiv_atom_errors_limits_entity_rejection_and_public_paper_ids(self):
        from relink.providers.arxiv import ArxivError, ArxivProvider
        for body in ('not XML', feed(16), '<!DOCTYPE feed [<!ENTITY x "forest">]><feed>&x;</feed>',
                     feed().replace('http://arxiv.org/abs/', 'http://127.0.0.1/abs/')):
            with self.subTest(body=body[:50]), patch('relink.providers.arxiv.time.sleep'), self.assertRaises(ArxivError):
                ArxivProvider(self.client(lambda r: httpx.Response(200, text=body))).search(('forest',))
        with patch('relink.providers.arxiv.time.sleep'):
            papers, url, warnings = ArxivProvider(self.client(lambda r: httpx.Response(200, text=feed()))).search(('forest',))
        self.assertEqual(papers[0].id, 'https://arxiv.org/abs/2401.00000v1')
        self.assertEqual(papers[0].authors, ('A. Author',))
        self.assertEqual(papers[0].year, 2024)
        self.assertIn('abs:', httpx.URL(url).params['search_query'])
        self.assertFalse(warnings)

    def test_model_input_is_bounded_and_missing_abstracts_are_not_invented(self):
        requests = []
        rows = [work('W' + str(i), abstract=('forest climate ' * 1500)) for i in range(15)]
        rows[0]['abstract_inverted_index'] = None
        def handler(request):
            requests.append(request)
            if request.headers['host'] == 'api.openalex.org': return httpx.Response(200, json={'results': rows})
            if request.headers['host'] == 'export.arxiv.org': return httpx.Response(200, text=feed(15, abstract='forest climate ' * 1500))
            supplied = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['papers']
            self.assertLessEqual(sum(len(p['abstract']) for p in supplied), 48000)
            return model_response(ranking_rows(request))
        with patch('relink.providers.arxiv.time.sleep'):
            # Larger response allowance is only to construct long, bounded abstract fixtures.
            client = self.client(handler); client.max_body_bytes = 2 * 1024 * 1024
            result = search_papers('forest', client=client, settings=GeminiSettings(api_key='mock-secret'))
        self.assertEqual(result.ranking.status, 'ranked')
        self.assertEqual(result.missing_abstracts, 1)
        self.assertEqual(len(result.papers), 29)

    def test_bridge_record_merges_existing_doi_and_arxiv_groups_without_losing_sources(self):
        from relink.paper_ranking import deduplicate_papers
        first = Paper('https://openalex.org/W1', 'Published paper', 'forest climate', doi='10.1234/shared')
        second = Paper('https://arxiv.org/abs/2401.00001v1', 'Preprint', 'forest', source='arxiv')
        bridge = Paper('https://openalex.org/W2', 'Another record', 'forest climate', doi='10.1234/shared',
                       landing_url=second.id)
        unique = deduplicate_papers((first, second, bridge), ('forest', 'climate'))
        self.assertEqual(len(unique), 1)
        self.assertEqual(len(unique[0].provenance), 3)

    def test_populated_winning_urls_do_not_erase_other_records_arxiv_identity(self):
        from relink.paper_ranking import deduplicate_papers, paper_identities
        first = Paper('https://openalex.org/W1', 'Published paper', 'forest climate', doi='10.1234/shared',
                      landing_url='https://publisher.example/paper', pdf_url='https://publisher.example/paper.pdf')
        alias = Paper('https://openalex.org/W2', 'Same paper', 'forest', doi=first.doi,
                      landing_url='https://arxiv.org/abs/2401.00001v1', pdf_url='https://arxiv.org/pdf/2401.00001v1')
        preprint = Paper(alias.landing_url, 'Preprint', 'forest', source='arxiv')
        merged = deduplicate_papers((first, alias), ('forest', 'climate'))
        self.assertIn('arxiv:2401.00001', paper_identities(merged[0]))
        self.assertEqual(len(deduplicate_papers((*merged, preprint), ('forest', 'climate'))), 1)
        self.assertTrue(any(p.pdf_url == alias.pdf_url for p in merged[0].provenance))

    def test_full_source_page_can_have_more_even_when_one_record_is_skipped(self):
        for source in ('openalex', 'arxiv'):
            def handler(request):
                if request.headers['host'] == 'api.openalex.org':
                    rows = [work('W' + str(i)) for i in range(15)] if source == 'openalex' else []
                    if rows: rows[-1]['title'] = None
                    return httpx.Response(200, json={'results': rows})
                text = feed(15).replace('<title>Preprint 14</title>', '<title/>') if source == 'arxiv' else feed(0)
                return httpx.Response(200, text=text)
            with self.subTest(source=source):
                result = search_papers('forest', client=self.client(handler))
                self.assertEqual(len(result.papers), 14)
                self.assertTrue(result.has_more)
                self.assertTrue(next(p.has_more for p in result.providers if p.source == source))

    def test_semantic_synonym_result_can_rank_without_exact_keywords(self):
        def handler(request):
            if request.headers['host'] == 'api.openalex.org':
                return httpx.Response(200, json={'results': [work(abstract='Woodland canopy measurements and observations')]})
            if request.headers['host'] == 'export.arxiv.org': return httpx.Response(200, text=feed(0))
            return model_response(ranking_rows(request))
        result = search_papers('forest', client=self.client(handler), settings=GeminiSettings(api_key='mock-only'))
        self.assertEqual(result.ranking.status, 'ranked')
        self.assertEqual(len(result.papers), 1)
        self.assertEqual(result.papers[0].score, 0)

    def test_arxiv_calls_wait_between_requests_without_global_sleep_patching(self):
        from relink.providers import arxiv
        clock = SimpleNamespace(monotonic=Mock(side_effect=[11, 13, 14, 16]), sleep=Mock())
        client = Mock()
        with patch.object(arxiv, 'time', clock), patch.object(arxiv, '_LAST_REQUEST', 10):
            fetch_arxiv(client, 'https://export.arxiv.org/api/query')
            fetch_arxiv(client, 'https://export.arxiv.org/api/query')
        self.assertEqual([call.args[0] for call in clock.sleep.call_args_list], [2, 2])
