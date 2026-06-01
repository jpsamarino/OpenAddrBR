"""Location autocomplete using TextSearchEngine."""

from openaddrbr.core.models import CityInfo, NeighborhoodInfo
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.utils import normalize_text


class LocationSearch:
    """Fast autocomplete for Brazilian cities and neighborhoods.

    Args:
        text_engine: TextSearchEngine instance. Creates one if not provided.
    """

    def __init__(self, text_engine: TextSearchEngine | None = None):
        self._engine = text_engine or TextSearchEngine()

    def search_cities(self, query: str, limit: int = 10) -> list[CityInfo]:
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

    def search_neighborhoods(
        self, query: str, city_code: int, limit: int = 10
    ) -> list[NeighborhoodInfo]:
        """Search for neighborhoods by name within a specific city.

        Args:
            query: Neighborhood name to search for.
            city_code: IBGE city code to filter by.
            limit: Max results to return.

        Returns:
            List of NeighborhoodInfo matching the query.
        """
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._engine.search_neighborhoods(
            query_normalized, city_code=city_code, limit=limit
        )
        if not hits:
            return []

        neighborhoods = []
        for hit in hits:
            neighborhood = self._engine.get_neighborhood(hit.doc_address)
            if neighborhood is not None:
                neighborhoods.append(neighborhood)
        return neighborhoods