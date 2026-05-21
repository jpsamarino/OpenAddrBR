"""Neighborhood autocomplete search using Tantivy ngram index."""

from openaddrbr.core.models import NeighborhoodInfo

def search_neighborhood_tantivy(query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
    return []