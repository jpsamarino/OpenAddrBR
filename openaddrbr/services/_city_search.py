"""City autocomplete using Tantivy ngram index."""

from openaddrbr.core.models import CityInfo
from openaddrbr.data import TantivySearch
from openaddrbr.utils import normalize_text


class CitySearch:
    """City autocomplete using tantivy ngram index.

    Args:
        tantivy_engine: TantivySearch instance. Must have data_path configured.

    Example:
        engine = TantivySearch("city_index", data_path="/path/to/data")
        search = CitySearch(tantivy_engine=engine)
        results = search.search("ARACAJU")
    """

    def __init__(self, tantivy_engine: TantivySearch):
        self._engine = tantivy_engine

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

        searcher = self._engine.searcher()

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


def search_city_tantivy(query: str, engine: TantivySearch, limit: int = 10) -> list[CityInfo]:
    """Search for cities using ngram autocomplete.

    Args:
        query: City name to search for.
        engine: TantivySearch instance configured with city_index.
        limit: Max results to return.

    Returns:
        List of CityInfo matching the query.
    """
    return CitySearch(tantivy_engine=engine).search(query, limit)