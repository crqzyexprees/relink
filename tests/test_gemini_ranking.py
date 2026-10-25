"""Source-bound ranking references, with mocked HTTP and no real credentials."""
import json
import unittest

import httpx

from relink.network import PublicHTTPClient
from relink.paper_models import Paper, RankedPaper
from relink.providers.gemini_ranking import GeminiPaperRanker


def response(rows, *, finish='STOP'):
    return httpx.Response(200, json={'candidates': [{'finishReason': finish,
        'content': {'parts': [{'text': json.dumps({'ranking': rows})}]}}]})


def paper(index=1, abstract=None):
    text = abstract if abstract is not None else ' '.join('term' + str(i) for i in range(90))
    return RankedPaper(Paper('https://openalex.org/W' + str(index), 'A real mocked title', text), 10, ('term1',), ('term1',))


class GeminiRankingTests(unittest.TestCase):
    def rank(self, handler, papers=None):
        with PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14']) as client:
            return GeminiPaperRanker(client, api_key='mock-only-key').rank('research topic', papers or (paper(),))

    def test_model_selects_actual_short_passages_instead_of_copying_quotes(self):
        received = []
        def handler(request):
            payload = json.loads(request.content)
            received.append(json.loads(payload['contents'][0]['parts'][0]['text']))
            return response([{'id': f'p{i:03d}', 'evidence_id': 1, 'reason': 'Relevant methods in this abstract.'}
                             for i in range(30, 0, -1)])
        ordered, info = self.rank(handler, tuple(paper(i) for i in range(1, 31)))
        self.assertEqual(info.status, 'ranked')
        self.assertEqual(len(ordered), 30)
        for row in received[0]['papers']:
            self.assertNotIn('title', row)
            self.assertNotIn('abstract', row)  # No duplicated source text alongside passages.
            self.assertTrue(row['abstract_passages'])
        for result, supplied in zip(ordered, reversed(received[0]['papers'])):
            self.assertEqual(result.semantic_evidence, supplied['abstract_passages'][0]['text'])
            self.assertLessEqual(len(result.semantic_evidence.split()), 16)
            self.assertLessEqual(len(result.semantic_evidence), 240)
            self.assertIn(result.semantic_evidence, result.paper.abstract)

    def test_invalid_passage_references_have_clear_safe_reasons_and_no_accepted_ranking(self):
        for reference in (0, -1, 999999, True, '1', None):
            with self.subTest(reference=reference):
                ordered, info = self.rank(lambda r: response([
                    {'id': 'p001', 'evidence_id': reference, 'reason': 'Relevant methods.'}]))
                self.assertEqual(info.status, 'invalid_response')
                self.assertIn('evidence passage', info.detail)
                self.assertFalse(ordered)

    def test_free_form_quotes_are_rejected_even_when_they_look_plausible(self):
        ordered, info = self.rank(lambda r: response([
            {'id': 'p001', 'evidence_id': 1, 'quote': 'invented evidence', 'reason': 'Relevant methods.'}]))
        self.assertFalse(ordered)
        self.assertEqual(info.status, 'invalid_response')
        self.assertNotIn('invented evidence', info.detail)

    def test_passage_ids_are_bound_to_the_selected_paper_after_reordering(self):
        originals = (paper(1, 'Forest canopy measurements across woodland sites.'),
                     paper(2, 'Ocean salinity observations from coastal monitoring.'))
        ordered, info = self.rank(lambda r: response([
            {'id': 'p002', 'evidence_id': 1, 'reason': 'Coastal monitoring methods.'},
            {'id': 'p001', 'evidence_id': 1, 'reason': 'Woodland observations.'}]), originals)
        self.assertEqual(info.status, 'ranked')
        self.assertEqual(ordered[0].paper.id, originals[1].paper.id)
        self.assertEqual(ordered[0].semantic_evidence, originals[1].paper.abstract)
        self.assertEqual(ordered[1].semantic_evidence, originals[0].paper.abstract)

    def test_later_passage_selection_and_other_papers_passage_ids(self):
        originals = (paper(1, 'Short forest observations.'), paper(2))
        valid = [{'id': 'p001', 'evidence_id': 1, 'reason': 'Forest observations.'},
                 {'id': 'p002', 'evidence_id': 2, 'reason': 'Later methods passage.'}]
        ordered, info = self.rank(lambda r: response(valid), originals)
        self.assertEqual(info.status, 'ranked')
        self.assertEqual(ordered[1].semantic_evidence, ' '.join('term' + str(i) for i in range(16, 32)))
        # Passage 2 exists for p002, but must never authorize it for p001.
        invalid = [dict(valid[0], evidence_id=2), valid[1]]
        ordered, info = self.rank(lambda r: response(invalid), originals)
        self.assertFalse(ordered)
        self.assertIn('evidence passage', info.detail)

    def test_control_tokens_do_not_join_source_words_across_a_gap(self):
        received = []
        def handler(request):
            rows = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['papers']
            received.extend(rows[0]['abstract_passages'])
            return response([{'id': 'p001', 'evidence_id': 2, 'reason': 'Actual canopy measurements.'}])
        ordered, info = self.rank(handler, (paper(abstract='Forest observations bad\x00token canopy measurements'),))
        self.assertEqual(info.status, 'ranked')
        self.assertEqual([p['text'] for p in received], ['Forest observations', 'canopy measurements'])
        self.assertEqual(ordered[0].semantic_evidence, 'canopy measurements')

    def test_over_limit_paper_count_does_not_make_a_request(self):
        ordered, info = self.rank(lambda r: self.fail('No request expected'), tuple(paper(i) for i in range(31)))
        self.assertFalse(ordered)
        self.assertEqual(info.status, 'invalid_response')
        self.assertIn('30-paper', info.detail)

    def test_large_unicode_payload_stays_within_the_transport_byte_limit(self):
        received_sizes = []
        def handler(request):
            received_sizes.append(len(request.content))
            rows = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['papers']
            return response([{'id': row['id'], 'evidence_id': 1, 'reason': 'Actual Unicode source text.'} for row in rows])
        ordered, info = self.rank(handler, tuple(paper(i, '🌳 ' * 5000) for i in range(30)))
        self.assertEqual(info.status, 'ranked')
        self.assertEqual(len(ordered), 30)
        self.assertLessEqual(received_sizes[0], 256 * 1024)

    def test_incomplete_order_and_token_limit_have_distinct_diagnostics(self):
        ordered, info = self.rank(lambda r: response([]))
        self.assertFalse(ordered)
        self.assertIn('paper count', info.detail)
        ordered, info = self.rank(lambda r: response([], finish='MAX_TOKENS'))
        self.assertFalse(ordered)
        self.assertIn('output token limit', info.detail)

    def test_bad_envelope_and_long_reasons_do_not_expose_raw_model_data(self):
        for payload in (httpx.Response(200, text='mock-only-key'), response([
            {'id': 'p001', 'evidence_id': 1, 'reason': 'mock-only-key' * 40}])):
            with self.subTest(payload=payload.status_code):
                ordered, info = self.rank(lambda r: payload)
                self.assertFalse(ordered)
                self.assertEqual(info.status, 'invalid_response')
                self.assertNotIn('mock-only-key', info.detail)

    def test_unicode_whitespace_long_tokens_and_text_budgets_preserve_source_evidence(self):
        received = []
        texts = ['測定 気候 \n woodland\tmeasurements ' * 1000,
                 'forest observations ' + 'z' * 500 + ' canopy measurements']
        def handler(request):
            rows = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])['papers']
            received.extend(rows)
            return response([{'id': row['id'], 'evidence_id': 1, 'reason': 'Relevant observations.'} for row in rows])
        original = tuple(paper(i, text) for i, text in enumerate(texts, 1))
        ordered, info = self.rank(handler, original)
        self.assertEqual(info.status, 'ranked')
        self.assertLessEqual(sum(len(p['text']) for row in received for p in row['abstract_passages']), 48000)
        for result, row in zip(ordered, received):
            normalized = ' '.join(result.paper.abstract.split())
            for passage in row['abstract_passages']:
                self.assertIn(passage['text'], normalized)
                self.assertLessEqual(len(passage['text']), 240)
                self.assertLessEqual(len(passage['text'].split()), 16)

    def test_no_usable_passage_does_not_make_a_model_request(self):
        for abstract in ('   ', 'z' * 500):
            with self.subTest(abstract=abstract[:10]):
                ordered, info = self.rank(lambda r: self.fail('No request expected'), (paper(abstract=abstract),))
                self.assertFalse(ordered)
                self.assertEqual(info.status, 'no_abstracts')
