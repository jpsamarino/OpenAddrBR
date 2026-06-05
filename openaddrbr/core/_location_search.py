"""Location autocomplete using TextSearchEngine."""

from openaddrbr.core.models import CityInfo, NeighborhoodInfo, StreetInfo
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
    ) -> list[StreetInfo]:
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

        # Parse all street_ids from hits
        all_street_ids: set[int] = set()
        hit_scores: dict[int, float] = {}
        for hit in hits:
            street_doc = self._engine.get_street(hit.doc_address)
            if street_doc:
                street_ids_str = street_doc.get("street_ids", "")
                if street_ids_str:
                    sid_list = [int(s) for s in street_ids_str.split(",") if s.isdigit()]
                    for sid in sid_list:
                        if sid not in hit_scores or hit.score > hit_scores[sid]:
                            hit_scores[sid] = hit.score
                    all_street_ids.update(sid_list)

        if not all_street_ids:
            return []

        # Bulk lookup from DB - StreetInfo has neighborhood_normalized
        street_infos = self._addr_store.query_streets_by_ids(all_street_ids)
        if not street_infos:
            return []

        # Build results with scores
        results_with_scores = []
        for info in street_infos:
            base_score = hit_scores.get(info.street_id, 0.0)
            results_with_scores.append((info, base_score))

        # Apply neighborhood bonus if provided (using StreetInfo.neighborhood_normalized)
        if neighborhood:
            neighborhood_norm = normalize_text(neighborhood)
            for i, (info, base_score) in enumerate(results_with_scores):
                if info.neighborhood_normalized and neighborhood_norm in info.neighborhood_normalized:
                    results_with_scores[i] = (info, base_score + 0.5)

        # Sort by weighted score descending
        results_with_scores.sort(key=lambda x: x[1], reverse=True)

        # Return top 'limit' results
        return [info for info, score in results_with_scores[:limit]]
