"""Location autocomplete using TextSearchEngine."""

from openaddrbr.core.models import CityInfo, NeighborhoodInfo, StreetSegmentInfo
from openaddrbr.data import SqlAddressDataStore
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.utils import normalize_text, text_similarity


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

        doc_addresses = [hit.doc_address for hit in hits]
        cities_data = self._engine.get_cities_batch(doc_addresses)
        return [c for c in cities_data if c is not None]

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

        doc_addresses = [hit.doc_address for hit in hits]
        neighborhoods_data = self._engine.get_neighborhoods_batch(doc_addresses)
        return [n for n in neighborhoods_data if n is not None]

    def search_streets(
        self,
        city_code: int,
        query: str,
        neighborhood: str | None = None,
        limit: int = 10,
        autocomplete_query: bool = False,
    ) -> list[StreetSegmentInfo]:
        """Search for streets by name within a specific city, with optional neighborhood boost.
        Args:
            city_code: IBGE city code to filter by.
            query: Street name to search for.
            neighborhood: Optional neighborhood name to boost results that match it.
            limit: Maximum number of distinct streets to return (may return more rows if the same street exists in multiple neighborhoods).
            autocomplete_query: Whether to treat the query as an autocomplete prefix.
        Returns:
            List of StreetSegmentInfo matching the query, sorted by relevance.
        """
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._engine.search_streets(
            query_normalized, city_code, limit=limit, autocomplete_query=autocomplete_query
        )
        if not hits:
            return []

        doc_addresses = [hit.doc_address for hit in hits]
        hit_scores: dict[int, float] = {}
        query_ids_list = self._engine.get_query_ids_batch(doc_addresses)
        query_ids: list[int] = [qid for qid in query_ids_list if qid is not None]

        for hit, qid in zip(hits, query_ids_list):
            if qid is not None:
                if qid not in hit_scores or hit.score > hit_scores[qid]:
                    hit_scores[qid] = hit.score

        if not query_ids:
            return []

        segments = self._addr_store.query_streets_by_query_id(query_ids)
        if not segments:
            return []

        results_with_scores = []
        for seg in segments:
            base_score = hit_scores.get(seg.street_id, 0.0)
            results_with_scores.append((seg, base_score))

        if neighborhood:
            neighborhood_norm = normalize_text(neighborhood)
            for i, (seg, base_score) in enumerate(results_with_scores):
                if seg.neighborhood_normalized:
                    sim = text_similarity(neighborhood_norm, seg.neighborhood_normalized)
                    boost = sim * 0.5
                    results_with_scores[i] = (seg, base_score + boost)

        results_with_scores.sort(key=lambda x: x[1], reverse=True)

        return [seg for seg, score in results_with_scores]

    def autocomplete_street(
        self,
        city_code: int,
        query: str,
        limit: int = 10,
    ) -> list[str]:
        """Ultra-fast street name autocomplete using only Tantivy index.

        Args:
            city_code: IBGE city code to filter by.
            query: Street name prefix/partial query.
            limit: Maximum number of results to return.

        Returns:
            List of unique street names matching the query, ordered by relevance.
            No SQLite lookup - pure Tantivy-only for maximum speed.
        """
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._engine.search_streets(
            query_normalized, city_code, limit=limit, autocomplete_query=True
        )
        if not hits:
            return []

        doc_addresses = [hit.doc_address for hit in hits]
        names = self._engine.get_street_names_batch(doc_addresses)

        # Filter empty strings and deduplicate while preserving order
        seen: set[str] = set()
        unique_names: list[str] = []
        for name in names:
            if name and name not in seen:
                seen.add(name)
                unique_names.append(name)

        return unique_names[:limit]
