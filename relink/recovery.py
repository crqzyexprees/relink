"""URL recovery orchestration, independent of UI and provider implementation."""

from collections.abc import Iterable

from relink.models import (DiscoveryProvider, DiscoveryResult, HashEvidence, ProviderResult,
                           RecoveryProvider, RecoveryResult, SearchQuery)
from relink.network import PublicHTTPClient, validate_url
from relink.providers.internet_archive import InternetArchiveProvider
from relink.providers.datacite import DataCiteProvider
from relink.ranking import rank_candidates
from relink.gemini_config import GeminiSettings
from relink.dataset_ai import assess_datasets
from relink.verification import check_current_url


def recover_url(original_url: str, *, client: PublicHTTPClient | None = None,
                provider: RecoveryProvider | None = None) -> RecoveryResult:
    """Check current access and query a provider, preserving independent outcomes.

    Invalid input raises UnsafeURLError. Network/provider failures are returned
    as explicit statuses. The caller owns an injected client's lifecycle.
    """
    validate_url(original_url)
    if client is None:
        with PublicHTTPClient() as owned_client:
            return recover_url(original_url, client=owned_client, provider=provider)
    current = check_current_url(original_url, client)
    if current.status == 'blocked':
        archive = ProviderResult('blocked', 'internet_archive',
                                 detail='Archive lookup skipped because the URL access check was blocked.')
    else:
        archive = (provider or InternetArchiveProvider(client)).search(original_url)
    return RecoveryResult(original_url, current, archive)


def discover_datasets(query: SearchQuery, *, client: PublicHTTPClient | None = None,
                      providers: Iterable[DiscoveryProvider] | None = None,
                      hash_evidence: Iterable[HashEvidence] = (), settings: GeminiSettings | None = None) -> DiscoveryResult:
    """Search, merge and rank metadata; keep each provider's independent outcome."""
    if client is None:
        with PublicHTTPClient() as owned_client:
            return discover_datasets(query, client=owned_client, providers=providers, hash_evidence=hash_evidence, settings=settings)
    if providers is None:
        providers = [DataCiteProvider(client, limit=30, page_size=15, max_pages=2)]
        if query.original_url:
            providers.append(InternetArchiveProvider(client))
    outcomes = tuple(provider.discover(query) for provider in providers)
    ranked = tuple(rank_candidates(query, (candidate for result in outcomes for candidate in result.candidates),
                                   hash_evidence=hash_evidence))
    applicable = [result for result in outcomes if result.status != 'not_applicable']
    errors = [result for result in applicable if result.status not in ('found', 'not_found')]
    if ranked:
        status = 'partial' if errors else 'found'
    elif errors or not applicable:
        status = 'error'
    else:
        status = 'not_found'
    ranked, assessment = assess_datasets(query, ranked, client=client, settings=settings)
    return DiscoveryResult(status, ranked, outcomes,
        'Relevance points are not probabilities. Provider metadata and sampled rows do not verify dataset preservation.', assessment)
