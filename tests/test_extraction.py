"""Real local PDF parsing; no HTTP or remote fixtures."""

import importlib.util
import unittest

from relink import extraction
from tests.pdf_fixtures import make_pdf


class TextLinkTests(unittest.TestCase):
    def test_trailing_prose_punctuation_is_not_part_of_url(self):
        links = extraction.extract_text_links('Data (https://example.org/data.csv). Also https://example.org/a_(b).')
        self.assertEqual([link.url for link in links], ['https://example.org/data.csv', 'https://example.org/a_(b)'])

    def test_wrapped_link_is_joined_with_an_explicit_warning(self):
        links = extraction.extract_text_links('Data at https://example.org/\ndata.csv')
        self.assertEqual(links[0].url, 'https://example.org/data.csv')
        self.assertTrue(links[0].occurrences[0].joined_lines)

    def test_local_addresses_and_non_web_links_are_excluded(self):
        links = extraction.extract_text_links('http://localhost/data http://127.0.0.1/x https://example.org/data.csv mailto:x@example.org')
        self.assertEqual([link.url for link in links], ['https://example.org/data.csv'])


@unittest.skipUnless(importlib.util.find_spec('pymupdf'), 'PyMuPDF is not installed')
class PDFTests(unittest.TestCase):
    def test_text_and_annotation_duplicates_retain_both_methods(self):
        result = extraction.extract_pdf_links(make_pdf(annotation='https://example.org/data.csv'))
        self.assertEqual(result.page_count, 1)
        self.assertEqual(len(result.links), 1)
        self.assertEqual({o.method for o in result.links[0].occurrences}, {'text', 'annotation'})
        self.assertEqual(result.links[0].occurrences[0].page, 1)
        self.assertIn('Dataset', result.links[0].occurrences[0].context)

    def test_annotation_link_does_not_need_visible_url_text(self):
        result = extraction.extract_pdf_links(make_pdf('Download the measurements', annotation='https://example.org/measurements.zip'))
        self.assertEqual(result.links[0].url, 'https://example.org/measurements.zip')

    def test_invalid_empty_and_oversized_pdfs_raise_clear_errors(self):
        for content, limit in [(b'', 100), (b'not a pdf', 100), (make_pdf(), 10)]:
            with self.subTest(content=content[:15]), self.assertRaises(extraction.PDFExtractionError):
                extraction.extract_pdf_links(content, max_bytes=limit)

    def test_empty_page_is_identified_as_not_extractable_text(self):
        result = extraction.extract_pdf_links(make_pdf(''))
        self.assertEqual(result.links, ())
        self.assertTrue(result.warnings)
        self.assertFalse(result.has_text)

    def test_text_without_links_is_an_honest_empty_result(self):
        result = extraction.extract_pdf_links(make_pdf('There are no research links here.'))
        self.assertEqual(result.links, ())
        self.assertTrue(result.has_text)

    def test_encrypted_pdf_is_not_silently_empty(self):
        import pymupdf
        with pymupdf.open(stream=make_pdf(), filetype='pdf') as document:
            encrypted = document.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw='owner', user_pw='reader')
        with self.assertRaisesRegex(extraction.PDFExtractionError, 'password'):
            extraction.extract_pdf_links(encrypted)

    def test_page_limit_is_enforced(self):
        with self.assertRaises(extraction.PDFExtractionError):
            extraction.extract_pdf_links(make_pdf(), max_pages=0)
