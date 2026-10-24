"""URL recovery orchestration, independent of UI and provider implementation."""

from relink.models import ProviderResult, RecoveryProvider, RecoveryResult
from relink.network import PublicHTTPClient, validate_url
from relink.providers.internet_archive import InternetArchiveProvider
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
