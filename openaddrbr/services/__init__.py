"""Services package - business logic services."""

from openaddrbr.services._cep import is_multi_street_cep, search_by_cep
from openaddrbr.services._city import get_city_info
from openaddrbr.services._city_search import CitySearch, search_city_tantivy
from openaddrbr.services._encoder import Encoder, VALID_BACKENDS
from openaddrbr.services._neighborhood_search import NeighborhoodSearch, search_neighborhood_tantivy
from openaddrbr.services._result_builder import _NormalizedAddr, _build_result
from openaddrbr.services._vector_search import search_by_embedding

__all__ = [
    "Encoder",
    "VALID_BACKENDS",
    "get_city_info",
    "search_by_cep",
    "is_multi_street_cep",
    "search_by_embedding",
    "CitySearch",
    "NeighborhoodSearch",
    "search_city_tantivy",
    "search_neighborhood_tantivy",
    "_build_result",
    "_NormalizedAddr",
]