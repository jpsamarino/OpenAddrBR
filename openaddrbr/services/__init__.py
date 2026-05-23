"""Services package - business logic services."""

from openaddrbr.services._cep import resolve_street_by_cep
from openaddrbr.services._city import get_city_info
from openaddrbr.services._encoder import VALID_BACKENDS, Encoder
from openaddrbr.services._geocode_result import build_result, find_best_geo_location
from openaddrbr.services._suggestions import LocationSuggestions
from openaddrbr.services._vector_search import search_by_embedding

__all__ = [
    "Encoder",
    "LocationSuggestions",
    "build_result",
    "find_best_geo_location",
    "get_city_info",
    "resolve_street_by_cep",
    "search_by_embedding",
    "VALID_BACKENDS",
]