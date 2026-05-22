"""Services package - business logic services."""

from openaddrbr.services._cep import search_by_cep
from openaddrbr.services._city import get_city_info
from openaddrbr.services._city_search import CitySearch, search_city_tantivy
from openaddrbr.services._encoder import VALID_BACKENDS, Encoder
from openaddrbr.services._geocode_result import build_result, find_best_geo_location
from openaddrbr.services._neighborhood_search import NeighborhoodSearch, search_neighborhood_tantivy
from openaddrbr.services._vector_search import search_by_embedding

__all__ = [
    "CitySearch",
    "Encoder",
    "NeighborhoodSearch",
    "build_result",
    "find_best_geo_location",
    "get_city_info",
    "search_by_cep",
    "search_by_embedding",
    "search_city_tantivy",
    "search_neighborhood_tantivy",
    "VALID_BACKENDS",
]