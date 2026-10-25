"""Model-suggested paper mentions are independent of recovered resource identity."""
from dataclasses import dataclass

from relink.models import RankedCandidate, SearchResult


@dataclass(frozen=True)
class DatasetMention:
    name: str
    version: str
    page: int
    quote: str
    quote_source: str = 'gemini_checked'


@dataclass(frozen=True)
class DatasetIdentification:
    status: str
    mentions: tuple[DatasetMention, ...] = ()
    detail: str = ''
    model: str = ''
    retrieved_at: str = ''
    warnings: tuple[str, ...] = ()
    retry_after: str | None = None


@dataclass(frozen=True)
class NamedDatasetSearch:
    mention: DatasetMention
    result: SearchResult
    ranked: tuple[RankedCandidate, ...] = ()
