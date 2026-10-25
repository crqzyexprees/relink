"""Primitive sample and assessment snapshots, independent of candidate models."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class DatasetPreview:
    status: str
    url: str = ''
    retrieved_at: str = ''
    headers: tuple[str, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    bytes_read: int = 0
    detail: str = ''
    truncated: bool = False
    response_metadata: dict = field(default_factory=dict)
    candidate_id: str = ''


@dataclass(frozen=True)
class DatasetAssessment:
    status: str
    detail: str = ''
    model: str = ''
    retrieved_at: str = ''
    retry_after: str | None = None
    previews: tuple[DatasetPreview, ...] = ()
    warnings: tuple[str, ...] = ()
