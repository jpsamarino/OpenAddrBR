"""Neighborhood autocomplete using Tantivy ngram index."""

from openaddrbr.core.models import NeighborhoodInfo
from openaddrbr.data import TantivySearch
from openaddrbr.utils import normalize_text


class NeighborhoodSearch:
    """Neighborhood autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch | None = None):
        self._ts = tantivy_search or TantivySearch("neighborhood_index")

    def search(self, query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
        """Search for neighborhoods by name within city."""
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._ts.search_text_by_city(
            query_normalized, "neighborhood_search", city_code=city_code, limit=limit
        )
        if not hits:
            return []

        searcher = self._ts.searcher()

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


# Cached instance
_neighborhood_search = NeighborhoodSearch()


def search_neighborhood_tantivy(
    query: str, city_code: int, limit: int = 10
) -> list[NeighborhoodInfo]:
    """Search for neighborhoods by name within city (backward compat)."""
    return _neighborhood_search.search(query, city_code, limit)