"""Offline paper search and selected-paper dataset lookup; HTTP/DNS are mocked."""
import unittest
from unittest.mock import patch

import httpx

from relink.network import PublicHTTPClient
from relink.paper_models import Paper
from relink.papers import lookup_paper_datasets, search_papers
from tests.pdf_fixtures import make_pdf
from tests.test_datacite import record


def work(identifier='W1', title='A paper', abstract='climate forest observations', **kwargs):
    index = {}
    for position, token in enumerate(abstract.split()):
        index.setdefault(token, []).append(position)
    return dict(id='https://openalex.org/' + identifier, title=title,
                doi='https://doi.org/10.1234/paper' + identifier, publication_year=2020,
                authorships=[{'author': {'display_name': 'A. Researcher'}}],
                abstract_inverted_index=index, primary_location={'landing_page_url': 'https://example.org/paper'},
                best_oa_location={'pdf_url': 'https://example.org/paper.pdf'}, **kwargs)


class PaperTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in offline test'))
        guard.start()
        self.addCleanup(guard.stop)

    def client(self, handler):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(client.close)
        return client

    def test_abstract_matching_outranks_title_and_preserves_source(self):
        rows = [work('W1', title='climate forest', abstract='unrelated ocean salinity'),
                work('W2', title='Different title', abstract='climate forest observations'),
                work('W3', title='Another paper', abstract='forest measurements')]
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={'results': rows, 'meta': {'count': 3}})
        result = search_papers('I want research on climate forest', client=self.client(handler))
        self.assertEqual(result.status, 'found')
        self.assertEqual([p.paper.id for p in result.papers], ['https://openalex.org/W2', 'https://openalex.org/W3'])
        self.assertEqual(result.papers[0].matched_terms, ('climate', 'forest'))
        self.assertEqual(result.papers[0].paper.abstract, 'climate forest observations')
        self.assertEqual(result.papers[0].paper.doi, '10.1234/paperw2')
        self.assertEqual(result.papers[0].paper.source, 'openalex')
        self.assertIn('search.title_and_abstract', requests[0].url.params)
        self.assertNotIn('I want research', str(requests[0].url))

    def test_missing_malformed_and_duplicate_records_do_not_become_matches(self):
        missing = work('W1'); missing['abstract_inverted_index'] = None
        malformed = work('W2'); malformed['abstract_inverted_index'] = {'forest': [10**9]}
        good = work('W3')
        result = search_papers('forest', client=self.client(lambda r: httpx.Response(200, json={
            'results': [missing, malformed, good, good]})))
        self.assertEqual(len(result.papers), 1)
        self.assertEqual(result.missing_abstracts, 1)
        self.assertTrue(result.warnings)

    def test_duplicate_doi_keeps_best_abstract_instead_of_first_record(self):
        rows = [work('W1', abstract='ocean'), work('W2', abstract='forest climate')]
        for row in rows: row['doi'] = 'https://doi.org/10.1234/same'
        result = search_papers('forest climate', client=self.client(lambda r: httpx.Response(200, json={'results': rows})))
        self.assertEqual(len(result.papers), 1)
        self.assertEqual(result.papers[0].paper.id, 'https://openalex.org/W2')

    def test_response_limits_and_abstract_position_validation(self):
        from relink.providers.openalex import reconstruct_abstract
        for index in ({'forest': [-1]}, {'forest': [True]}, {'forest': [0], 'climate': [0]},
                      {'forest': [2]}, {'forest': 'bad'}):
            with self.subTest(index=index), self.assertRaises(ValueError): reconstruct_abstract(index)
        result = search_papers('forest', client=self.client(lambda r: httpx.Response(200, json={'results': [work()] * 26})))
        self.assertEqual(result.status, 'invalid_response')

    def test_empty_errors_rate_limit_timeout_and_bad_json_are_distinct(self):
        for response, expected in [(httpx.Response(200, json={'results': []}), 'not_found'),
                                    (httpx.Response(429, headers={'Retry-After': '60'}), 'rate_limited'),
                                    (httpx.Response(403), 'error'), (httpx.Response(500), 'error'),
                                    (httpx.Response(200, text='not JSON'), 'invalid_response')]:
            with self.subTest(status=expected):
                result = search_papers('forest', client=self.client(lambda r: response))
                self.assertEqual(result.status, expected)
                self.assertFalse(result.papers)
                if expected == 'rate_limited': self.assertEqual(result.retry_after, '60')
        def timeout(request): raise httpx.ReadTimeout('mock timeout', request=request)
        self.assertEqual(search_papers('forest', client=self.client(timeout)).status, 'timeout')

    def test_invalid_topics_do_not_make_requests_and_query_syntax_is_not_injected(self):
        client = self.client(lambda r: self.fail('No request expected'))
        for topic in ('', 'the and I want papers', 'x' * 1201, 'forest\x00'):
            with self.subTest(topic=topic[:15]), self.assertRaises(ValueError):
                search_papers(topic, client=client)
        seen = []
        def handler(request):
            seen.append(request.url.params['search.title_and_abstract'])
            return httpx.Response(200, json={'results': []})
        search_papers('forest OR * NOT climate', client=self.client(handler))
        self.assertEqual(seen, ['"forest" OR "climate"'])

    def test_selected_paper_uses_related_doi_and_real_pdf_links(self):
        requests = []
        pdf = make_pdf('Dataset: https://example.org/data.csv')
        paper = Paper(id='https://openalex.org/W1', title='A paper', doi='10.1234/paper',
                      pdf_url='https://example.org/paper.pdf')
        def handler(request):
            requests.append(request)
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
            return httpx.Response(200, content=pdf)
        result = lookup_paper_datasets(paper, client=self.client(handler))
        self.assertEqual(result.pdf_status, 'extracted')
        self.assertEqual(result.links[0].url, 'https://example.org/data.csv')
        self.assertEqual(len(result.datasets.candidates), 1)
        self.assertIn('relatedIdentifiers.relatedIdentifier', requests[0].url.params['query'])
        self.assertEqual(result.paper_id, paper.id)

    def test_missing_pdf_and_doi_keep_abstract_links_without_network(self):
        paper = Paper(id='https://openalex.org/W1', title='A paper',
                      abstract='Data at https://example.org/data.csv')
        result = lookup_paper_datasets(paper, client=self.client(lambda r: self.fail('No request expected')))
        self.assertEqual(result.pdf_status, 'unavailable')
        self.assertEqual(result.datasets.status, 'not_applicable')
        self.assertEqual(result.links[0].url, 'https://example.org/data.csv')

    def test_own_paper_doi_aliases_are_not_dataset_links(self):
        paper = Paper(id='https://openalex.org/W1', title='A paper', doi='10.1234/paper',
                      abstract='Paper http://dx.doi.org/10.1234/PAPER Dataset https://doi.org/10.1234/data')
        result = lookup_paper_datasets(paper, client=self.client(lambda r: httpx.Response(
            200, json={'data': [], 'meta': {'total': 0}})))
        self.assertEqual([link.url for link in result.links], ['https://doi.org/10.1234/data'])

    def test_deep_json_is_a_provider_error_not_an_uncaught_exception(self):
        result = search_papers('forest', client=self.client(lambda r: httpx.Response(
            200, content=b'[' * 15000 + b']' * 15000)))
        self.assertEqual(result.status, 'invalid_response')

    def test_pdf_timeout_and_missing_dataset_metadata_remain_explicit(self):
        paper = Paper(id='https://openalex.org/W1', title='A paper', doi='10.1234/paper',
                      pdf_url='https://example.org/paper.pdf')
        def handler(request):
            if request.headers['host'] == 'api.datacite.org':
                return httpx.Response(200, json={'data': [], 'meta': {'total': 0}})
            raise httpx.ReadTimeout('mock PDF timeout', request=request)
        result = lookup_paper_datasets(paper, client=self.client(handler))
        self.assertEqual(result.pdf_status, 'timeout')
        self.assertEqual(result.datasets.status, 'not_found')
        self.assertFalse(result.links)

    def test_datacite_failure_does_not_discard_pdf_dataset_links(self):
        paper = Paper(id='https://openalex.org/W1', title='A paper', doi='10.1234/paper',
                      pdf_url='https://example.org/paper.pdf')
        def handler(request):
            if request.headers['host'] == 'api.datacite.org': return httpx.Response(503)
            return httpx.Response(200, content=make_pdf('Dataset https://example.org/data.csv'))
        result = lookup_paper_datasets(paper, client=self.client(handler))
        self.assertEqual(result.datasets.status, 'error')
        self.assertEqual(result.pdf_status, 'extracted')
        self.assertEqual(result.links[0].url, 'https://example.org/data.csv')

    def test_unsafe_redirect_bad_pdf_and_timeout_preserve_independent_metadata(self):
        paper = Paper(id='https://openalex.org/W1', title='A paper', doi='10.1234/paper',
                      pdf_url='https://example.org/paper.pdf')
        for response, status in [(httpx.Response(302, headers={'Location': 'http://127.0.0.1/secret'}), 'blocked'),
                                 (httpx.Response(200, text='<html>paywall</html>'), 'invalid_pdf'),
                                 (httpx.Response(429, headers={'Retry-After': '30'}), 'rate_limited')]:
            def handler(request):
                if request.headers['host'] == 'api.datacite.org':
                    return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
                return response
            with self.subTest(status=status):
                result = lookup_paper_datasets(paper, client=self.client(handler))
                self.assertEqual(result.pdf_status, status)
                self.assertTrue(result.datasets.candidates)
