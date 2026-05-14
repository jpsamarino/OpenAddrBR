"""Compatibility shim - wraps function-based API into class."""

from openaddrbr import geocode as _geocode
from openaddrbr.core.models import StreetCluster
from openaddrbr.data import (
    query_street_query,
)
from openaddrbr.data import (
    search_vector as _search_vector_index,
)
from openaddrbr.services._cep import (
    is_multi_street_cep as _is_multi_street_cep,
)
from openaddrbr.services._cep import (
    search_by_cep as _search_by_cep,
)
from openaddrbr.services._city import get_city_info as _get_city_info


class IBGEGeocoder:
    """Compatibility wrapper that mimics old IBGEGeocoder class API."""

    def __init__(self, verbose=True, preload_model=True):
        self._verbose = verbose
        self._preload_model = preload_model

    def get_city_info(self, city_name, state_code):
        return _get_city_info(city_name, state_code)

    def is_multi_street_cep(self, cep):
        return _is_multi_street_cep(cep)

    def search_by_cep(self, zip_code, street_norm, neighborhood_norm, limit_qt_street=10):
        return _search_by_cep(zip_code, street_norm, neighborhood_norm, limit_qt_street)

    def geocode(self, street, neighborhood, city, state, zip_code=None, number=0):
        return _geocode(street, neighborhood, city, state, zip_code, number)

    def search_vector(self, embedding, city_code, limit=20):
        """Search for street by vector similarity using usearch."""
        query_ids = _search_vector_index(embedding, city_code, limit=limit)
        if not query_ids:
            return []

        return query_street_query(query_ids)

    def get_geo_info_batch(self, addresses, batch_size=16):
        from openaddrbr import get_geo_info_batch as _batch

        return _batch(addresses, batch_size)


__all__ = ["IBGEGeocoder"]
