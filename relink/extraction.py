"""Bounded, local PDF link extraction. No network access or OCR."""

from dataclasses import dataclass
import re

from relink.network import UnsafeURLError, validate_url


MAX_PDF_BYTES = 10 * 1024 * 1024
URL_PATTERN = re.compile(r'https?://[^\s<>"{}]+', re.I)
WRAPPED_URL = re.compile(r'(https?://[^\s<>"{}]*[/_?&=%.-])\r?\n([A-Za-z0-9_~%/?=&.\-]+)')


class PDFExtractionError(ValueError):
    """An upload could not be safely processed as a readable PDF."""


@dataclass(frozen=True)
class LinkOccurrence:
    page: int
    context: str
    method: str
    joined_lines: bool = False


@dataclass(frozen=True)
class ExtractedLink:
    url: str
    occurrences: tuple[LinkOccurrence, ...]


@dataclass(frozen=True)
class TextPage:
    number: int
    text: str


@dataclass(frozen=True)
class PDFExtraction:
    page_count: int
    links: tuple[ExtractedLink, ...]
    title: str | None = None
    has_text: bool = False
    warnings: tuple[str, ...] = ()
    pages: tuple[TextPage, ...] = ()


def _clean_url(value: str) -> str:
    value = value.rstrip('.,;:!?')
    for opening, closing in [('(', ')'), ('[', ']')]:
        while value.endswith(closing) and value.count(closing) > value.count(opening):
            value = value[:-1].rstrip('.,;:!?')
    return value


def extract_text_links(text: str, *, page: int = 1) -> list[ExtractedLink]:
    """Find public-looking HTTP(S) links and retain surrounding text evidence.

    DNS is not resolved during extraction. The recovery transport will validate
    DNS before requests. Wrapped URLs are conservative guesses, flagged for review.
    """
    joined = text
    for _ in range(4):
        updated = WRAPPED_URL.sub(r'\1\2', joined)
        if updated == joined:
            break
        joined = updated
    links: dict[str, list[LinkOccurrence]] = {}
    for match in URL_PATTERN.finditer(joined):
        raw = _clean_url(match.group())
        try:
            url = str(validate_url(raw))
        except UnsafeURLError:
            continue
        context = ' '.join(joined[max(0, match.start() - 160):match.end() + 160].split())
        links.setdefault(url, []).append(LinkOccurrence(page, context, 'text', joined != text and raw not in text))
    return [ExtractedLink(url, tuple(occurrences)) for url, occurrences in links.items()]


def extract_pdf_links(content: bytes, *, max_bytes: int = MAX_PDF_BYTES,
                      max_pages: int = 100, max_links: int = 250,
                      max_text_chars: int = 1_000_000) -> PDFExtraction:
    if not isinstance(content, bytes) or not content:
        raise PDFExtractionError('The PDF is empty. Choose a readable research paper.')
    if len(content) > max_bytes:
        raise PDFExtractionError(f'The PDF exceeds the {max_bytes / (1024 * 1024):g} MB upload limit.')
    if b'%PDF-' not in content[:1024]:
        raise PDFExtractionError('This file is not a PDF.')
    if max_links < 1 or max_text_chars < 1:
        raise PDFExtractionError('PDF extraction limits must be positive.')
    try:
        import pymupdf
    except ImportError as exc:
        raise PDFExtractionError('PDF support requires PyMuPDF. Install the project requirements and restart the app.') from exc
    links: dict[str, list[LinkOccurrence]] = {}
    warnings = []
    has_text = False
    text_chars = 0
    pages = []

    def add(url, occurrence):
        if url not in links and len(links) >= max_links:
            message = f'Only the first {max_links} unique links are shown.'
            if message not in warnings:
                warnings.append(message)
            return
        occurrences = links.setdefault(url, [])
        if occurrence not in occurrences:
            occurrences.append(occurrence)

    try:
        with pymupdf.open(stream=content, filetype='pdf') as document:
            if document.needs_pass:
                raise PDFExtractionError('This PDF requires a password. Upload an unlocked copy.')
            if document.page_count > max_pages:
                raise PDFExtractionError(f'The PDF exceeds the {max_pages}-page limit. Upload a shorter paper.')
            if not document.page_count:
                raise PDFExtractionError('The PDF has no pages.')
            title = document.metadata.get('title')
            title = title.strip() if isinstance(title, str) and title.strip() else None
            for page_number, pdf_page in enumerate(document, 1):
                text = pdf_page.get_text('text', sort=True)
                text_chars += len(text)
                if text_chars > max_text_chars:
                    raise PDFExtractionError('The PDF contains too much text to analyze in this session.')
                pages.append(TextPage(page_number, text))
                has_text = has_text or bool(text.strip())
                for link in extract_text_links(text, page=page_number):
                    for occurrence in link.occurrences:
                        add(link.url, occurrence)
                annotations = pdf_page.get_links()
                if len(annotations) > 1000:
                    warnings.append(f'Page {page_number}: only the first 1,000 annotations were examined.')
                for annotation in annotations[:1000]:
                    uri = annotation.get('uri')
                    if not uri:
                        continue
                    try:
                        url = str(validate_url(uri))
                    except UnsafeURLError:
                        continue
                    rectangle = pymupdf.Rect(annotation['from'])
                    rectangle = pymupdf.Rect(rectangle.x0 - 60, rectangle.y0 - 30,
                                             rectangle.x1 + 60, rectangle.y1 + 30)
                    context = ' '.join(pdf_page.get_text('text', clip=rectangle).split())[:400]
                    add(url, LinkOccurrence(page_number, context, 'annotation'))
            page_count = document.page_count
    except PDFExtractionError:
        raise
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        raise PDFExtractionError('The PDF could not be read. It may be malformed or damaged.') from exc
    if not has_text:
        warnings.append('No searchable text was found. OCR is not available; any embedded links are still listed.')
    if any(occurrence.joined_lines for occurrences in links.values() for occurrence in occurrences):
        warnings.append('Some line-wrapped URLs were joined heuristically. Check the selected URL before recovering.')
    return PDFExtraction(page_count, tuple(ExtractedLink(url, tuple(items)) for url, items in links.items()),
                         title, has_text, tuple(warnings), tuple(pages))
