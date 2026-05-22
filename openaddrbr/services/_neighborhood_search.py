"""Neighborhood autocomplete using Tantivy ngram index."""

from openaddrbr.core.models import NeighborhoodInfo
from openaddrbr.data import TantivySearch
from openaddrbr.utils import normalize_text


class NeighborhoodSearch:
    """Neighborhood autocomplete using Tantivy ngram index.

    Args:
        tantivy_engine: TantivySearch instance. Must have data_path configured.

    Example:
        engine = TantivySearch("neighborhood_index", data_path="/path/to/data")
        search = NeighborhoodSearch(tantivy_engine=engine)
        results = search.search("CENTRO", city_code=1100015)
    """

    def __init__(self, tantivy_engine: TantivySearch):
        self._engine = tantivy_engine

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

        hits = self._engine.search_neighborhoods(
            query_normalized, city_code=city_code, limit=limit
        )
        if not hits:
            return []

        searcher = self._engine.searcher()

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
    query: str, city_code: int, engine: TantivySearch, limit: int = 10
) -> list[NeighborhoodInfo]:
    """Search for neighborhoods by name within city.

    Args:
        query: Neighborhood name to search for.
        city_code: IBGE city code to filter by.
        engine: TantivySearch instance configured with neighborhood_index.
        limit: Max results to return.

    Returns:
        List of NeighborhoodInfo matching the query.
    """
    return NeighborhoodSearch(tantivy_engine=engine).search(query, city_code, limit)