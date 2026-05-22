"""City autocomplete using TextSearchEngine."""

from openaddrbr.core.models import CityInfo
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.utils import normalize_text


class CitySearch:
    """City autocomplete using TextSearchEngine.

    Args:
        text_engine: TextSearchEngine instance with city_index loaded.
    """

    def __init__(self, text_engine: TextSearchEngine):
        self._engine = text_engine

    def search(self, query: str, limit: int = 10) -> list[CityInfo]:
        """Search for cities by name using ngram autocomplete.

        Args:
            query: City name to search for.
            limit: Max results to return.

        Returns:
            List of CityInfo matching the query.
        """
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._engine.search_cities(query_normalized, limit=limit)
        if not hits:
            return []

        cities = []
        for hit in hits:
            city = self._engine.get_city(hit.doc_address)
            if city is not None:
                cities.append(city)
        return cities


def search_city_tantivy(query: str, engine: TextSearchEngine, limit: int = 10) -> list[CityInfo]:
    """Search for cities using ngram autocomplete.

    Args:
        query: City name to search for.
        engine: TextSearchEngine instance.
        limit: Max results to return.

    Returns:
        List of CityInfo matching the query.
    """
    return CitySearch(text_engine=engine).search(query, limit)