"""Paper discovery contracts, separate from dataset identity/verification."""
from dataclasses import dataclass

from relink.extraction import ExtractedLink
from relink.models import SearchResult
from relink.gemini_models import DatasetIdentification, NamedDatasetSearch


@dataclass(frozen=True)
class Paper:
    id: str
    title: str
    abstract: str = ''
    authors: tuple[str, ...] = ()
    year: int | None = None
    doi: str = ''
    landing_url: str = ''
    pdf_url: str = ''
    source: str = 'openalex'
    retrieved_at: str = ''


@dataclass(frozen=True)
class RankedPaper:
    paper: Paper
    score: int
    matched_terms: tuple[str, ...]
    query_terms: tuple[str, ...]


@dataclass(frozen=True)
class PaperSearchResult:
    status: str
    papers: tuple[RankedPaper, ...] = ()
    detail: str = ''
    query_url: str = ''
    retrieved_count: int = 0
    missing_abstracts: int = 0
    warnings: tuple[str, ...] = ()
    retry_after: str | None = None


@dataclass(frozen=True)
class PaperDatasetLookup:
    paper_id: str
    datasets: SearchResult
    links: tuple[ExtractedLink, ...] = ()
    pdf_status: str = 'unavailable'
    detail: str = ''
    identification: DatasetIdentification | None = None
    named_searches: tuple[NamedDatasetSearch, ...] = ()
