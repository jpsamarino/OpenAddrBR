"""Services package - CEP and city services."""

from openaddrbr.services._cep import is_multi_street_cep, search_by_cep
from openaddrbr.services._city import get_city_info

__all__ = [
    "get_city_info",
    "search_by_cep",
    "is_multi_street_cep",
]
