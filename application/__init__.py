"""Compatibility shim - wraps function-based API into class."""

from pathlib import Path

from openaddrbr import geocode as _geocode
from openaddrbr.core._env import get_default_data_path
from openaddrbr.core.models import StreetCluster
from openaddrbr.data import SQLDB as Database
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.data._usearch import UsearchIndex
from openaddrbr.services._cep import (
    is_multi_street_cep as _is_multi_street_cep,
)
from openaddrbr.services._cep import (
    search_by_cep as _search_by_cep,
)
from openaddrbr.services._city import get_city_info as _get_city_info
from openaddrbr.services._vector_search import search_by_embedding


class IBGEGeocoder:
    """Compatibility wrapper that mimics old IBGEGeocoder class API.

    Args:
        data_path: Path to data directory. Defaults to env var or package default.
        verbose: Enable verbose logging.
        preload_model: Preload encoder model on init.
    """

    def __init__(
        self,
        data_path: Path | str | None = None,
        verbose: bool = True,
        preload_model: bool = True,
    ):
        self._data_path = Path(data_path) if data_path else get_default_data_path()
        self._verbose = verbose
        self._preload_model = preload_model

        self._db = Database(data_path=self._data_path)
        self._usearch = UsearchIndex(data_path=self._data_path)
        self._city_engine = TantivySearch("city_index", data_path=self._data_path)
        self._neighborhood_engine = TantivySearch(
            "neighborhood_index", data_path=self._data_path
        )

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
        return search_by_embedding(
            city_code=city_code,
            embedding=embedding,
            street_norm=None,
            neighborhood_norm=None,
            db=self._db,
            usearch_index=self._usearch,
        )

    def get_geo_info_batch(self, addresses, batch_size=16):
        from openaddrbr import get_geo_info_batch as _batch

        return _batch(addresses, batch_size)


__all__ = ["IBGEGeocoder"]