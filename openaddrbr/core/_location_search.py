"""Location autocomplete using TextSearchEngine."""

from openaddrbr.core.models import CityInfo, NeighborhoodInfo, StreetSegmentInfo
from openaddrbr.data import SqlAddressDataStore
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.utils import normalize_text


class LocationSearch:
    """Fast autocomplete for Brazilian cities and neighborhoods.

    Args:
        text_engine: TextSearchEngine instance. Creates one if not provided.
    """

    def __init__(
        self,
        text_engine: TextSearchEngine | None = None,
        addr_store: SqlAddressDataStore | None = None,
    ):
        self._engine = text_engine or TextSearchEngine()
        self._addr_store = addr_store or SqlAddressDataStore()

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

        hits = self._engine.search_neighborhoods(query_normalized, city_code=city_code, limit=limit)
        if not hits:
            return []

        neighborhoods = []
        for hit in hits:
            neighborhood = self._engine.get_neighborhood(hit.doc_address)
            if neighborhood is not None:
                neighborhoods.append(neighborhood)
        return neighborhoods

    def search_streets(
        self,
        city_code: int,
        query: str,
        neighborhood: str | None = None,
        limit: int = 10,
    ) -> list[StreetSegmentInfo]:
        """Search for streets by name using ngram autocomplete.

        Args:
            city_code: IBGE city code.
            query: Street name to search for.
            neighborhood: Optional neighborhood for score boosting (not filtering).
            limit: Max results to return.

        Returns:
            List of StreetInfo matching the query, ordered by weighted score.
        """
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._engine.search_streets(query_normalized, city_code, limit=limit)
        if not hits:
            return []

        # Collect query_ids from hits (simpler than street_ids - no commas)
        query_ids: list[int] = []
        hit_scores: dict[int, float] = {}
        for hit in hits:
            street_doc = self._engine.get_street(hit.doc_address)
            if street_doc:
                query_id = street_doc.get("query_id")
                if query_id is not None:
                    query_ids.append(query_id)
                    if query_id not in hit_scores or hit.score > hit_scores[query_id]:
                        hit_scores[query_id] = hit.score

        if not query_ids:
            return []

        # Use query_streets_by_query_id for direct JOIN query
        segments = self._addr_store.query_streets_by_query_id(query_ids)
        if not segments:
            return []

        # Build results with scores (order from hit_scores)
        results_with_scores = []
        for seg in segments:
            # Use first matching hit score for this segment
            base_score = hit_scores.get(seg.street_id, 0.0)
            results_with_scores.append((seg, base_score))

        # Apply neighborhood bonus if provided
        if neighborhood:
            neighborhood_norm = normalize_text(neighborhood)
            for i, (seg, base_score) in enumerate(results_with_scores):
                if seg.neighborhood_normalized and neighborhood_norm in seg.neighborhood_normalized:
                    results_with_scores[i] = (seg, base_score + 0.5)

        # Sort by weighted score descending
        results_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top 'limit' results
        return [seg for seg, score in results_with_scores[:limit]]
