"""Offline public DataCite tests; payloads are fixtures, never live results."""

import socket
import unittest
from unittest.mock import patch

import httpx

from relink.models import Candidate, SearchQuery
from relink.network import PublicHTTPClient
from relink.providers.datacite import DataCiteProvider, build_query


def record(doi='10.1234/soil.v1', **attributes):
    values = {
        'doi': doi, 'url': 'https://repository.example/datasets/soil.csv',
        'titles': [{'title': 'Forest soil measurements'}],
        'creators': [{'name': 'Lovelace, Ada', 'affiliation': [{'name': 'Penn State University'}]}],
        'publisher': 'Example Repository', 'publicationYear': 2020,
        'types': {'resourceTypeGeneral': 'Dataset'}, 'version': '1.0',
        'descriptions': [{'description': 'Carbon measurements from temperate forests.'}],
        'relatedIdentifiers': [{'relatedIdentifier': 'https://old.example/soil.csv',
                                'relatedIdentifierType': 'URL', 'relationType': 'IsIdenticalTo'}],
    }
    values.update(attributes)
    return {'type': 'dois', 'id': doi, 'attributes': values}


class DataCiteTests(unittest.TestCase):
    def test_bounded_discovery_requests_relevance_order_from_the_service(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json={'data': [], 'meta': {'total': 0}})
        DataCiteProvider(self.client(handler)).discover(SearchQuery(description='penguin measurements'))
        self.assertEqual(calls[0].url.params['sort'], 'relevance')

    def test_deep_json_is_a_provider_error_not_an_uncaught_exception(self):
        result = DataCiteProvider(self.client(lambda r: httpx.Response(
            200, content=b'[' * 15000 + b']' * 15000))).discover(SearchQuery(title='forest'))
        self.assertEqual(result.status, 'invalid_response')

    def setUp(self):
        guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in offline test'))
        guard.start()
        self.addCleanup(guard.stop)

    def client(self, handler, resolver=None):
        client = PublicHTTPClient(transport=httpx.MockTransport(handler),
                                  resolver=resolver or (lambda h, p: ['93.184.215.14']))
        self.addCleanup(client.close)
        return client

    def test_all_search_fields_build_scoped_request_and_preserve_metadata(self):
        requests = []
        def handler(request):
            requests.append(request)
            return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
        query = SearchQuery(title='Forest soi', author='Ada Lovelace',
                            institution='Penn State University', year=2020,
                            original_url='https://old.example/soil.csv',
                            doi='https://doi.org/10.1234/SOIL.V1', description='carbon forests')
        result = DataCiteProvider(self.client(handler)).discover(query)
        self.assertEqual(result.status, 'found')
        self.assertEqual(requests[0].headers['host'], 'api.datacite.org')
        params = requests[0].url.params
        self.assertEqual(params['resource-type-id'], 'dataset')
        self.assertIn('titles.title:', params['query'])
        self.assertIn('creators.name:', params['query'])
        self.assertIn('creators.affiliation.name:', params['query'])
        self.assertIn('publicationYear:2020', params['query'])
        self.assertIn('relatedIdentifiers.relatedIdentifier:', params['query'])
        self.assertIn('suffix:', params['query'])
        self.assertIn('descriptions.description:', params['query'])
        candidate = result.candidates[0]
        self.assertIsInstance(candidate, Candidate)
        self.assertEqual(candidate.doi, '10.1234/soil.v1')
        self.assertEqual(candidate.url, 'https://repository.example/datasets/soil.csv')
        self.assertEqual(candidate.authors, ('Lovelace, Ada',))
        self.assertEqual(candidate.institutions, ('Penn State University',))
        self.assertEqual(candidate.year, 2020)
        self.assertEqual(candidate.filenames, ('soil.csv',))
        self.assertEqual(candidate.source, 'datacite')
        self.assertEqual(candidate.publisher, 'Example Repository')
        self.assertEqual(candidate.provenance[0].metadata['publisher'], 'Example Repository')

    def test_each_search_field_can_be_used_alone(self):
        for fields in [{'title': 'soil'}, {'author': 'Lovelace'}, {'institution': 'Penn State'},
                       {'year': 2020}, {'original_url': 'https://old.example/data.csv'},
                       {'doi': '10.1234/soil.v1'}, {'description': 'carbon observations'}]:
            with self.subTest(fields=fields):
                query = SearchQuery(**fields)
                self.assertTrue(build_query(query))
                result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={'data': []}))).discover(query)
                self.assertEqual(result.status, 'not_found')

    def test_search_text_cannot_inject_query_operators(self):
        query = build_query(SearchQuery(institution='Ada" OR *:* OR name:"x'))
        self.assertIn(r'\"', query)
        self.assertIn(r'\*\:\*', query)

    def test_author_search_handles_reversed_catalog_name_order(self):
        expression = build_query(SearchQuery(author='Ada Lovelace'))
        self.assertIn('creators.name:(Ada* AND Lovelace*)', expression)
        self.assertNotIn('"Ada Lovelace"', expression)

    def test_doi_resolver_input_does_not_require_matching_repository_landing_url(self):
        query = SearchQuery(original_url='https://doi.org/10.24432/C56C76', doi='10.24432/c56c76')
        expression = build_query(query)
        self.assertIn('prefix:', expression)
        self.assertIn('suffix:', expression)
        self.assertNotIn('url:', expression)

    def test_dataset_rights_are_requested_and_preserved_for_attribution_review(self):
        rights = [{'rights': 'Creative Commons Attribution 4.0', 'rightsUri': 'https://creativecommons.org/licenses/by/4.0/'}]
        def handler(request):
            self.assertIn('rightsList', request.url.params['fields[dois]'].split(','))
            return httpx.Response(200, json={'data': [record(rightsList=rights)], 'meta': {'total': 1}})
        result = DataCiteProvider(self.client(handler)).discover(SearchQuery(title='soil'))
        self.assertEqual(result.candidates[0].provenance[0].metadata['rightsList'], rights)

    def test_invalid_or_empty_search_is_rejected(self):
        for fields in [{}, {'title': '   '}, {'year': True}, {'year': 10000},
                       {'doi': 'nonsense'}, {'original_url': 'http://localhost/'}]:
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                DataCiteProvider(self.client(lambda r: self.fail('Invalid query sent'))).discover(SearchQuery(**fields))

    def test_sparse_metadata_and_old_affiliation_shapes_are_supported(self):
        row = record(titles=[], publicationYear=None, descriptions=None, url=None,
                     creators=[{'givenName': 'Ada', 'familyName': 'Lovelace',
                                'affiliation': ['Penn State University']}],
                     publisher={'name': 'Repository'})
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={'data': [row]}))).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'found')
        self.assertIsNone(result.candidates[0].url)
        self.assertEqual(result.candidates[0].authors, ('Ada Lovelace',))
        self.assertEqual(result.candidates[0].institutions, ('Penn State University',))

    def test_errors_never_become_not_found(self):
        for response, expected in [(httpx.Response(500), 'error'),
                                   (httpx.Response(403), 'error'),
                                   (httpx.Response(200, text='not json'), 'invalid_response'),
                                   (httpx.Response(200, json={}), 'invalid_response'),
                                   (httpx.Response(200, json={'data': {}}), 'invalid_response')]:
            with self.subTest(expected=expected):
                result = DataCiteProvider(self.client(lambda r: response)).discover(SearchQuery(title='soil'))
                self.assertEqual(result.status, expected)
                self.assertEqual(result.candidates, ())

    def test_timeout_dns_and_rate_limit_are_explicit(self):
        for error, expected in [(httpx.ReadTimeout('slow'), 'timeout'),
                                (socket.gaierror(socket.EAI_NONAME, 'missing'), 'dns_failure')]:
            def resolve(h, p):
                if isinstance(error, socket.gaierror):
                    raise error
                return ['93.184.215.14']
            def handler(request):
                raise error
            with self.subTest(expected=expected):
                result = DataCiteProvider(self.client(handler, resolve)).discover(SearchQuery(title='soil'))
                self.assertEqual(result.status, expected)
        calls = []
        def rate_limited(request):
            calls.append(request)
            return httpx.Response(429, headers={'Retry-After': '120'})
        result = DataCiteProvider(self.client(rate_limited)).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'rate_limited')
        self.assertEqual(result.retry_after, '120')
        self.assertEqual(len(calls), 1)

    def test_pagination_is_bounded_and_does_not_follow_untrusted_next_url(self):
        requests = []
        def handler(request):
            requests.append(request)
            n = request.url.params['page[number]']
            return httpx.Response(200, json={'data': [record(f'10.1234/soil.{n}')],
                'meta': {'total': 1000}, 'links': {'next': 'http://localhost/private'}})
        result = DataCiteProvider(self.client(handler), page_size=1, max_pages=2).discover(SearchQuery(title='soil'))
        self.assertEqual(len(result.candidates), 2)
        self.assertTrue(result.truncated)
        self.assertEqual([r.url.params['page[number]'] for r in requests], ['1', '2'])
        self.assertTrue(all(r.headers['host'] == 'api.datacite.org' for r in requests))

    def test_later_page_error_retains_candidates(self):
        def handler(request):
            if request.url.params['page[number]'] == '1':
                return httpx.Response(200, json={'data': [record()], 'meta': {'total': 2}})
            return httpx.Response(429, headers={'Retry-After': '20'})
        result = DataCiteProvider(self.client(handler), page_size=1).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual(result.http_status, 429)
        self.assertEqual(result.retry_after, '20')

    def test_malformed_records_are_reported_without_discarding_valid_records(self):
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={
            'data': [record(), {'attributes': {}}, record('10.1234/software', types={'resourceTypeGeneral': 'Software'})]
        }))).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.candidates), 1)
        self.assertTrue(result.warnings)

    def test_all_malformed_records_are_not_a_successful_empty_search(self):
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={
            'data': [{'attributes': {}}]}))).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'invalid_response')

    def test_nonzero_total_with_no_records_is_not_reported_as_not_found(self):
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={
            'data': [], 'meta': {'total': 2}}))).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'invalid_response')

    def test_inconsistent_record_doi_is_not_accepted(self):
        row = record()
        row['attributes']['doi'] = '10.1234/something_else'
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={
            'data': [row]}))).discover(SearchQuery(title='soil'))
        self.assertEqual(result.status, 'invalid_response')
        self.assertEqual(result.candidates, ())

    def test_candidate_limit_is_enforced(self):
        rows = [record(f'10.1234/soil.{n}') for n in range(5)]
        result = DataCiteProvider(self.client(lambda r: httpx.Response(200, json={
            'data': rows, 'meta': {'total': 5}})), limit=2).discover(SearchQuery(title='soil'))
        self.assertEqual(len(result.candidates), 2)
        self.assertTrue(result.truncated)
