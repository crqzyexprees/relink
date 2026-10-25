"""Shared candidate identity, ranking, and orchestration behavior."""

from dataclasses import replace
import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import httpx

from relink.candidates import deduplicate_candidates
from relink.models import Candidate, HashEvidence, RelatedIdentifier, SearchQuery
from relink.network import PublicHTTPClient
from relink.ranking import rank_candidates
from relink.recovery import discover_datasets
from relink.providers.internet_archive import InternetArchiveProvider
from tests.test_datacite import record


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        guard = patch('socket.getaddrinfo', side_effect=AssertionError('Live DNS in offline test'))
        guard.start()
        self.addCleanup(guard.stop)

    def candidate(self, **kwargs):
        defaults = dict(source='datacite', doi='10.1234/soil.v1',
                        url='https://repository.example/soil.csv',
                        titles=('Forest soil measurements',), authors=('Lovelace, Ada',),
                        institutions=('Penn State University',), year=2020,
                        filenames=('soil.csv',), descriptions=('Temperate forest carbon observations',))
        return Candidate(**(defaults | kwargs))

    def test_duplicate_doi_forms_merge_and_preserve_sources(self):
        a = self.candidate()
        b = self.candidate(source='future_repository', doi='https://doi.org/10.1234/SOIL.V1',
                           url='https://other.example/soil.csv')
        merged = deduplicate_candidates([a, b])
        self.assertEqual(len(merged), 1)
        self.assertEqual({p.source for p in merged[0].provenance}, {'datacite', 'future_repository'})
        self.assertEqual({p.url for p in merged[0].provenance},
                         {'https://repository.example/soil.csv', 'https://other.example/soil.csv'})

    def test_url_deduplication_does_not_merge_different_dois_or_paths(self):
        a = self.candidate(doi=None, url='https://EXAMPLE.org:443/data.csv#part')
        b = self.candidate(doi=None, url='https://example.org/data.csv')
        self.assertEqual(len(deduplicate_candidates([a, b])), 1)
        self.assertEqual(len(deduplicate_candidates([
            self.candidate(doi='10.1234/v1'), self.candidate(doi='10.1234/v2')])), 2)
        self.assertEqual(len(deduplicate_candidates([a, replace(b, url='https://example.org/DATA.csv')])) , 2)

    def test_only_root_empty_path_and_slash_are_canonicalized(self):
        a = self.candidate(doi=None, url='https://example.org')
        b = self.candidate(doi=None, url='https://example.org/')
        self.assertEqual(len(deduplicate_candidates([a, b])), 1)
        for first, second in [('https://example.org/a%2Fb', 'https://example.org/a/b'),
                              ('https://example.org/data', 'https://example.org/data/'),
                              ('https://example.org/?x=1', 'https://example.org/?x=2')]:
            with self.subTest(first=first, second=second):
                self.assertEqual(len(deduplicate_candidates([replace(a, url=first), replace(b, url=second)])), 2)

    def test_archive_uses_shared_candidate_without_losing_capture_fields(self):
        payload = {'archived_snapshots': {'closest': {'available': True, 'status': '200',
                   'timestamp': '20200102030405',
                   'url': 'https://web.archive.org/web/20200102030405/https://example.org/data.csv'}}}
        with PublicHTTPClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json=payload)),
                              resolver=lambda h, p: ['93.184.215.14']) as client:
            result = InternetArchiveProvider(client).discover(SearchQuery(original_url='https://example.org/data.csv'))
        self.assertIsInstance(result.candidates[0], Candidate)
        self.assertEqual(result.candidates[0].capture_timestamp, '20200102030405')
        self.assertEqual(result.candidates[0].url, result.candidates[0].archived_url)

    def test_ranking_prefers_supporting_evidence_and_explains_contributions(self):
        good = self.candidate()
        bad = self.candidate(doi='10.1234/unrelated', titles=('Ocean salinity',),
                             authors=('Someone Else',), year=2023, filenames=())
        query = SearchQuery(title='Forest soi', author='Ada Lovelace', year=2020,
                            institution='Penn State', original_url='https://old.example/soil.csv',
                            description='carbon forest observations')
        results = rank_candidates(query, [bad, good])
        self.assertEqual(results[0].candidate.doi, '10.1234/soil.v1')
        self.assertEqual(results[0].status, 'likely_match')
        signals = {item.signal: item for item in results[0].explanation}
        for name in ['title', 'author', 'institution', 'year', 'filename', 'url', 'description']:
            self.assertIn(name, signals)
        self.assertGreater(signals['filename'].points, 0)
        self.assertEqual(results[0].score, sum(e.points for e in results[0].explanation))
        self.assertEqual(results[1].status, 'unverified_candidate')

    def test_exact_doi_and_url_metadata_never_verify_a_candidate(self):
        candidate = self.candidate()
        result = rank_candidates(SearchQuery(doi=candidate.doi, original_url=candidate.url), [candidate])[0]
        self.assertEqual(result.status, 'likely_match')
        self.assertNotEqual(result.status, 'verified_exact_match')

    def test_partial_title_is_weaker_than_exact_and_not_identity_evidence_alone(self):
        query = SearchQuery(title='Iris', author='Fisher')
        wrong = self.candidate(doi='10.1234/irish', titles=('Irish census data',), authors=('Fisher',))
        right = self.candidate(doi='10.1234/iris', titles=('Iris',), authors=('Fisher',))
        ranked = rank_candidates(query, [wrong, right])
        self.assertEqual(ranked[0].candidate.doi, right.doi)
        self.assertEqual(ranked[1].status, 'unverified_candidate')
        self.assertLess(ranked[1].score, ranked[0].score)
        wrong_author = self.candidate(titles=('Iris',), authors=('Fisheries Institute',))
        self.assertEqual(rank_candidates(query, [wrong_author])[0].status, 'unverified_candidate')

    def test_provider_hash_claims_cannot_verify_a_candidate(self):
        row = record(hashes={'sha256': 'a' * 64}, verification_status='verified_exact_match')
        with PublicHTTPClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            'data': [row], 'meta': {'total': 1}})), resolver=lambda h, p: ['93.184.215.14']) as client:
            result = discover_datasets(SearchQuery(doi='10.1234/soil.v1'), client=client)
        self.assertEqual(result.candidates[0].status, 'likely_match')
        self.assertEqual(result.candidates[0].candidate.verification_status, 'metadata_only')

    def test_independent_matching_sha256_can_verify_only_its_candidate(self):
        candidate = self.candidate()
        evidence = HashEvidence(candidate_url=candidate.url, reference_sha256='a' * 64,
                                 candidate_sha256='a' * 64, reference_source='paper supplement',
                                 candidate_source='independent local file hash')
        result = rank_candidates(SearchQuery(title='soil'), [candidate], hash_evidence=[evidence])[0]
        self.assertEqual(result.status, 'verified_exact_match')
        for invalid in [replace(evidence, candidate_url='https://elsewhere.example/other.csv'),
                        replace(evidence, candidate_sha256='b' * 64),
                        replace(evidence, reference_source=evidence.candidate_source),
                        replace(evidence, reference_sha256='bad'),
                        replace(evidence, reference_source='')]:
            with self.subTest(evidence=invalid):
                self.assertNotEqual(rank_candidates(SearchQuery(title='soil'), [candidate],
                                                    hash_evidence=[invalid])[0].status, 'verified_exact_match')

    def test_independent_hash_agreement_outweighs_all_metadata_signals(self):
        exact = self.candidate(doi='10.1234/exact', url='https://repo.example/exact.csv',
                               titles=(), authors=(), institutions=(), year=None, filenames=(), descriptions=())
        metadata = self.candidate()
        evidence = HashEvidence(exact.url, 'a' * 64, 'a' * 64, 'published checksum', 'independent file calculation')
        query = SearchQuery(title='Forest soil measurements', author='Ada Lovelace',
                            institution='Penn State University', year=2020,
                            original_url=metadata.url, doi=metadata.doi, description='carbon observations')
        ranked = rank_candidates(query, [metadata, exact], hash_evidence=[evidence])
        self.assertEqual(ranked[0].candidate.doi, '10.1234/exact')
        self.assertEqual(ranked[0].status, 'verified_exact_match')

    def test_search_context_is_not_returned_url_identity_evidence(self):
        original = 'https://old.example/soil.csv'
        candidate = self.candidate(original_url=original)
        ranked = rank_candidates(SearchQuery(original_url=original), [candidate])[0]
        self.assertEqual(ranked.status, 'unverified_candidate')
        self.assertEqual(next(e.points for e in ranked.explanation if e.signal == 'url'), 0)

    def test_conflicting_hash_observations_cannot_verify(self):
        candidate = self.candidate()
        good = HashEvidence(candidate.url, 'a' * 64, 'a' * 64, 'reference', 'observed file')
        bad = replace(good, candidate_sha256='b' * 64)
        ranked = rank_candidates(SearchQuery(doi=candidate.doi), [candidate], hash_evidence=[good, bad])[0]
        self.assertEqual(ranked.status, 'unverified_candidate')

    def test_explicit_version_relation_is_different_version(self):
        candidate = self.candidate(doi='10.1234/soil.v2', related_identifiers=(
            RelatedIdentifier('10.1234/soil.v1', 'DOI', 'IsNewVersionOf'),))
        result = rank_candidates(SearchQuery(doi='10.1234/soil.v1'), [candidate])[0]
        self.assertEqual(result.status, 'different_version')
        self.assertTrue(any(e.signal == 'version' for e in result.explanation))

    def test_year_mismatch_alone_does_not_assert_a_different_version(self):
        result = rank_candidates(SearchQuery(title='Forest soil measurements', year=2019), [self.candidate()])[0]
        self.assertEqual(result.status, 'unverified_candidate')
        self.assertTrue(any(e.signal == 'year' and e.points < 0 for e in result.explanation))

    def test_ties_sort_deterministically(self):
        a, b = self.candidate(doi='10.1234/a'), self.candidate(doi='10.1234/b')
        q = SearchQuery(title='soil')
        first = [r.candidate.doi for r in rank_candidates(q, [a, b])]
        second = [r.candidate.doi for r in rank_candidates(q, [b, a])]
        self.assertEqual(first, second)

    def test_partial_provider_failure_keeps_usable_results(self):
        def handler(request):
            if request.headers['host'] == 'archive.org':
                return httpx.Response(503)
            return httpx.Response(200, json={'data': [record()], 'meta': {'total': 1}})
        with PublicHTTPClient(transport=httpx.MockTransport(handler),
                              resolver=lambda h, p: ['93.184.215.14']) as client:
            result = discover_datasets(SearchQuery(title='soil', original_url='https://old.example/soil.csv'), client=client)
        self.assertEqual(result.status, 'partial')
        self.assertEqual(len(result.candidates), 1)
        self.assertEqual({p.source for p in result.providers}, {'datacite', 'internet_archive'})

    def test_empty_results_and_service_failure_are_distinct(self):
        for code, expected in [(200, 'not_found'), (500, 'error')]:
            with self.subTest(code=code), PublicHTTPClient(
                transport=httpx.MockTransport(lambda r: httpx.Response(code, json={'data': []})),
                resolver=lambda h, p: ['93.184.215.14']) as client:
                result = discover_datasets(SearchQuery(title='soil'), client=client)
                self.assertEqual(result.status, expected)
                self.assertEqual(result.candidates, ())

    def test_discovery_cli_emits_structured_mocked_results(self):
        from scripts.discover_datasets import main
        with PublicHTTPClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={
            'data': [record()], 'meta': {'total': 1}})), resolver=lambda h, p: ['93.184.215.14']) as client:
            output = io.StringIO()
            with patch('scripts.discover_datasets.discover_datasets', side_effect=lambda q: discover_datasets(q, client=client)):
                with redirect_stdout(output):
                    exit_code = main(['--title', 'Forest soil', '--author', 'Ada Lovelace'])
        self.assertEqual(exit_code, 0)
        payload = json.loads(output.getvalue())
        self.assertEqual(payload['candidates'][0]['status'], 'likely_match')
        self.assertTrue(payload['candidates'][0]['explanation'])
