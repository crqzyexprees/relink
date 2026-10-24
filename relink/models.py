"""Evidence-bearing results shared by recovery providers and callers."""

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CurrentStatus:
    status: str
    final_url: str
    http_status: int | None = None
    redirects: tuple[str, ...] = ()
    retry_after: str | None = None
    detail: str = ''


@dataclass(frozen=True)
class RecoveryCandidate:
    original_url: str
    archived_url: str
    capture_timestamp: str
    source: str
    retrieved_at: str
    evidence: tuple[str, ...]
    verification_status: str = 'archive_metadata_only'
    limitation: str = (
        'The availability API reports a capture. Replay accessibility and '
        'downloadable dataset preservation have not been verified.'
    )


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
