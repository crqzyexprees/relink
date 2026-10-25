"""Core identification → real repository search. Model output is not a candidate."""
from relink.gemini_config import GeminiSettings
from relink.gemini_models import NamedDatasetSearch
from relink.models import SearchQuery, SearchResult
from relink.network import PublicHTTPClient
from relink.providers.datacite import DataCiteProvider
from relink.providers.gemini import GeminiProvider
from relink.ranking import rank_candidates


def identify_and_discover(pages, *, settings: GeminiSettings, client=None):
    if client is None:
        with PublicHTTPClient() as owned:
            return identify_and_discover(pages, settings=settings, client=owned)
    identification = GeminiProvider(client, api_key=settings.api_key, model=settings.model).identify(pages)
    searches = []
    for mention in identification.mentions[:3]:
        try:
            query = SearchQuery(title=mention.name, version=mention.version)
            result = DataCiteProvider(client, limit=5, page_size=5, max_pages=1).discover(query)
            ranked = tuple(rank_candidates(query, result.candidates))
        except ValueError:
            result = SearchResult('invalid_query', 'datacite', detail='This identified name could not form a supported repository query.')
            ranked = ()
        searches.append(NamedDatasetSearch(mention, result, ranked))
    return identification, tuple(searches)
