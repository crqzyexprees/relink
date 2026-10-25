"""Thin application workflow and report serialization over the existing engine."""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json

from relink.models import CurrentStatus, DiscoveryResult, SearchQuery, SearchResult
from relink.network import PublicHTTPClient, UnsafeURLError, validate_url
from relink.recovery import discover_datasets
from relink.gemini_models import DatasetIdentification, NamedDatasetSearch
from relink.verification import check_current_url
from relink.gemini_config import GeminiSettings


@dataclass(frozen=True)
class RecoveryReport:
    generated_at: str
    query: SearchQuery
    current: CurrentStatus
    discovery: DiscoveryResult
    input_context: dict = field(default_factory=dict)
    schema_version: int = 1
    identification: DatasetIdentification | None = None
    named_searches: tuple[NamedDatasetSearch, ...] = ()


def query_from_input(url: str, context: str = '') -> SearchQuery:
    """Normalize ordinary form whitespace before engine validation."""
    return SearchQuery(original_url=url.strip(), description=' '.join(context.split()))


def run_recovery(query: SearchQuery, *, input_context: dict | None = None,
                 on_progress: Callable[[str], None] | None = None,
                 client: PublicHTTPClient | None = None, settings: GeminiSettings | None = None) -> RecoveryReport:
    """Check current access, then invoke discovery once; never refetch on display."""
    if query.original_url: validate_url(query.original_url)
    if client is None:
        with PublicHTTPClient() as owned_client:
            return run_recovery(query, input_context=input_context, on_progress=on_progress, client=owned_client, settings=settings)
    if on_progress and query.original_url:
        on_progress('Checking the original URL')
    current = check_current_url(query.original_url, client) if query.original_url else CurrentStatus(
        'not_applicable', '', detail='Dataset metadata discovery; no original URL was supplied.')
    if current.status == 'blocked':
        result = SearchResult('blocked', 'request_policy', detail=current.detail)
        discovery = DiscoveryResult('error', (), (result,), 'Unsafe URL access was blocked. No provider search was made.')
    else:
        if on_progress:
            on_progress('Searching dataset sources, sampling advertised tables and assessing relevance')
        discovery = discover_datasets(query, client=client, settings=settings)
    return RecoveryReport(datetime.now(timezone.utc).isoformat(), query, current, discovery, input_context or {})


def report_json(report: RecoveryReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, indent=2, allow_nan=False)


def public_link(value: str | None) -> str | None:
    """Syntactic public-link policy for rendering; no DNS or HTTP during reruns."""
    if not isinstance(value, str):
        return None
    try:
        return str(validate_url(value))
    except UnsafeURLError:
        return None


def paper_dataset_report(lookup, title: str) -> RecoveryReport:
    """Presentation/export adapter for actual combined lookup results, no requests."""
    query = SearchQuery(description=('Datasets mentioned in ' + title)[:1200])
    stamp = lookup.combined.assessment.retrieved_at if lookup.combined and lookup.combined.assessment else ''
    return RecoveryReport(stamp, query, CurrentStatus('not_applicable', ''), lookup.combined,
                          {'mode': 'paper_datasets', 'paper_id': lookup.paper_id})
