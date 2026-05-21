"""City autocomplete using Tantivy ngram index."""

from openaddrbr.core._env import get_tantivy_dir
from openaddrbr.core.models import CityInfo
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.utils import normalize_text


class CitySearch:
    """City autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch | None = None):
        self._ts = tantivy_search or TantivySearch("city_index")

    def search(self, query: str, limit: int = 10) -> list[CityInfo]:
        """Search for cities by name using ngram autocomplete."""
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._ts.search_raw(query_normalized, "city_search", city_code=None, limit=limit)
        if not hits:
            return []

        index = self._ts._get_index()
        searcher = index.searcher()

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


# Backward compatibility function
def search_city_tantivy(query: str, limit: int = 10) -> list[CityInfo]:
    """Search for cities using ngram autocomplete (backward compat)."""
    return CitySearch().search(query, limit)