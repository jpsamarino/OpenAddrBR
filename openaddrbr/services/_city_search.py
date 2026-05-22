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

        # Get searcher from the city_index
        city_index = self._engine._get_city_index()
        searcher = city_index.searcher()

        cities = []
        for score, doc_address in hits:
            doc = searcher.doc(doc_address)
            city_name = doc.get_first("city_name") or ""
            cities.append(
                CityInfo(
                    city_code=doc.get_first("city_code"),
                    city_name=city_name,
                    city_normalized=normalize_text(city_name),
                    state_code=doc.get_first("state_code"),
                    latitude=doc.get_first("ref_latitude"),
                    longitude=doc.get_first("ref_longitude"),
                )
            )
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