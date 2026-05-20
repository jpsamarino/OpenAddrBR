"""City autocomplete search using Tantivy ngram index."""

from openaddrbr.core.models import CityInfo


def search_city_tantivy(query: str, limit: int = 10) -> list[CityInfo]:
    """Search cities using ngram autocomplete. Stub that returns empty list."""
    return []