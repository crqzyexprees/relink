"""Evidence-bearing results shared by recovery providers and callers."""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol
from relink.dataset_models import DatasetAssessment


@dataclass(frozen=True)
class CurrentStatus:
    status: str
    final_url: str
    http_status: int | None = None
    redirects: tuple[str, ...] = ()
    retry_after: str | None = None
    detail: str = ''


@dataclass(frozen=True)
class CandidateProvenance:
    source: str
    url: str | None = None
    doi: str | None = None
    record_id: str | None = None
    retrieved_at: str = ''
    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class RelatedIdentifier:
    identifier: str
    identifier_type: str
    relation_type: str


@dataclass(frozen=True)
class Candidate:
    # These first six fields retain the original Archive result contract.
    original_url: str = ''
    archived_url: str | None = None
    capture_timestamp: str | None = None
    source: str = ''
    retrieved_at: str = ''
    evidence: tuple[str, ...] = ()
    verification_status: str = 'metadata_only'
    limitation: str = (
        'Metadata is a discovery lead. Resource accessibility, dataset identity, '
        'and downloadable dataset preservation have not been verified.'
    )
    url: str | None = None
    doi: str | None = None
    titles: tuple[str, ...] = ()
    authors: tuple[str, ...] = ()
    institutions: tuple[str, ...] = ()
    publisher: str | None = None
    year: int | None = None
    filenames: tuple[str, ...] = ()
    descriptions: tuple[str, ...] = ()
    version: str | None = None
    related_identifiers: tuple[RelatedIdentifier, ...] = ()
    provenance: tuple[CandidateProvenance, ...] = ()

    def __post_init__(self):
        if not self.provenance:
            object.__setattr__(self, 'provenance', (CandidateProvenance(
                self.source, self.url or self.archived_url, self.doi,
                self.doi or self.url or self.archived_url, self.retrieved_at),))


# Backwards-compatible name for existing URL recovery callers.
RecoveryCandidate = Candidate


@dataclass(frozen=True)
class ProviderResult:
    status: str
    source: str
    candidate: RecoveryCandidate | None = None
    detail: str = ''
    http_status: int | None = None
    retry_after: str | None = None


class RecoveryProvider(Protocol):
    def search(self, original_url: str) -> ProviderResult:
        """Search for surviving evidence without claiming dataset identity."""
        ...


@dataclass(frozen=True)
class RecoveryResult:
    original_url: str
    current: CurrentStatus
    archive: ProviderResult


@dataclass(frozen=True)
class SearchQuery:
    title: str = ''
    author: str = ''
    institution: str = ''
    year: int | None = None
    original_url: str = ''
    doi: str = ''
    description: str = ''
    filenames: tuple[str, ...] = ()
    version: str = ''

    def __post_init__(self):
        from relink.identifiers import normalize_doi
        from relink.network import validate_url
        for value in (self.title, self.author, self.institution, self.description, self.doi, self.version):
            if not isinstance(value, str) or len(value) > 2000 or any(ord(c) < 32 for c in value):
                raise ValueError('Search fields must be short text without control characters.')
        if self.year is not None and (type(self.year) is not int or not 1000 <= self.year <= 9999):
            raise ValueError('Publication year must be a four-digit integer.')
        if self.doi and not normalize_doi(self.doi):
            raise ValueError('Supply a DOI or DOI resolver URL.')
        if self.original_url:
            validated_url = validate_url(self.original_url)
            inferred_doi = normalize_doi(str(validated_url))
            if not self.doi and inferred_doi:
                object.__setattr__(self, 'doi', inferred_doi)
        if not isinstance(self.filenames, tuple) or any(
            not isinstance(name, str) or not name.strip() or len(name) > 255 for name in self.filenames
        ):
            raise ValueError('Filenames must be a tuple of short names.')
        if not any((self.title.strip(), self.author.strip(), self.institution.strip(),
                    self.year, self.original_url, self.doi, self.description.strip(), self.filenames)):
            raise ValueError('Provide at least one dataset search field.')


@dataclass(frozen=True)
class SearchResult:
    status: str
    source: str
    candidates: tuple[Candidate, ...] = ()
    detail: str = ''
    http_status: int | None = None
    retry_after: str | None = None
    query_url: str | None = None
    truncated: bool = False
    warnings: tuple[str, ...] = ()


class DiscoveryProvider(Protocol):
    def discover(self, query: SearchQuery) -> SearchResult:
        """Return shared candidates, preserving service failures and provenance."""
        ...


class MatchStatus(StrEnum):
    VERIFIED_EXACT_MATCH = 'verified_exact_match'
    LIKELY_MATCH = 'likely_match'
    DIFFERENT_VERSION = 'different_version'
    UNVERIFIED_CANDIDATE = 'unverified_candidate'
    NOT_FOUND = 'not_found'


@dataclass(frozen=True)
class RankingEvidence:
    signal: str
    points: int
    detail: str
    query_values: tuple[str, ...] = ()
    candidate_values: tuple[str, ...] = ()


@dataclass(frozen=True)
class HashEvidence:
    """Trusted caller supplies reference and independently computed file hashes.

    Providers must never populate this from catalog metadata. Evidence is scoped
    to the candidate URL and must describe the same complete resource on both
    sides; the ranking layer does not download or authenticate file bytes.
    """
    candidate_url: str
    reference_sha256: str
    candidate_sha256: str
    reference_source: str
    candidate_source: str


@dataclass(frozen=True)
class RankedCandidate:
    candidate: Candidate
    score: int
    status: MatchStatus
    explanation: tuple[RankingEvidence, ...]
    ai_rank: int | None = None
    ai_reason: str = ''
    ai_evidence: str = ''
    ai_field: str = ''


@dataclass(frozen=True)
class DiscoveryResult:
    status: str
    candidates: tuple[RankedCandidate, ...]
    providers: tuple[SearchResult, ...]
    detail: str
    assessment: DatasetAssessment | None = None
