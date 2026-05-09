"""Compatibility shim - wraps function-based API into class."""

from openaddrbr import geocode as _geocode
from openaddrbr.services._city import get_city_info as _get_city_info
from openaddrbr.services._cep import (
    search_by_cep as _search_by_cep,
    is_multi_street_cep as _is_multi_street_cep,
)
from openaddrbr.data import (
    search_vector as _search_vector_index,
    query_street_query,
    get_connection,
)
from openaddrbr.core.models import StreetCluster


class IBGEGeocoder:
    """Compatibility wrapper that mimics old IBGEGeocoder class API."""

    def __init__(self, verbose=True, preload_model=True):
        self._verbose = verbose
        self._preload_model = preload_model
        self._sgeodb_conn = None

    def _get_sgeodb(self):
        """Compatibility - return connection from data layer."""
        if self._sgeodb_conn is None:
            self._sgeodb_conn = get_connection()
        return self._sgeodb_conn

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

        return query_street_query(query_ids, city_code)

    def get_geo_info_batch(self, addresses, batch_size=16):
        from openaddrbr import get_geo_info_batch as _batch

        return _batch(addresses, batch_size)

    def close(self):
        """Close database connection."""
        if self._sgeodb_conn:
            self._sgeodb_conn = None


__all__ = ["IBGEGeocoder"]
