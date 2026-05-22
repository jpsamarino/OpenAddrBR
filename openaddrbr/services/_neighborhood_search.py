"""Neighborhood autocomplete using TextSearchEngine."""

from openaddrbr.core.models import NeighborhoodInfo
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.utils import normalize_text


class NeighborhoodSearch:
    """Neighborhood autocomplete using TextSearchEngine.

    Args:
        text_engine: TextSearchEngine instance with neighborhood_index loaded.
    """

    def __init__(self, text_engine: TextSearchEngine):
        self._engine = text_engine

    def search(self, query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
        """Search for neighborhoods by name within city.

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

        hits = self._engine.search_neighborhoods(query_normalized, city_code=city_code, limit=limit)
        if not hits:
            return []

        searcher = self._engine._get_neighborhood_index().searcher()

        neighborhoods = []
        for score, doc_address in hits:
            doc = searcher.doc(doc_address)
            neighborhood_name = doc.get_first("neighborhood_name") or ""
            neighborhoods.append(
                NeighborhoodInfo(
                    neighborhood_name=neighborhood_name,
                    neighborhood_normalized=normalize_text(neighborhood_name),
                    city_code=doc.get_first("city_code"),
                    latitude=doc.get_first("ref_latitude"),
                    longitude=doc.get_first("ref_longitude"),
                )
            )
        return neighborhoods


def search_neighborhood_tantivy(
    query: str, city_code: int, engine: TextSearchEngine, limit: int = 10
) -> list[NeighborhoodInfo]:
    """Search for neighborhoods by name within city.

    Args:
        query: Neighborhood name to search for.
        city_code: IBGE city code to filter by.
        engine: TextSearchEngine instance.
        limit: Max results to return.

    Returns:
        List of NeighborhoodInfo matching the query.
    """
    return NeighborhoodSearch(text_engine=engine).search(query, city_code, limit)