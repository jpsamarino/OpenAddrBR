"""Protocol definitions for structural subtyping."""

from typing import TYPE_CHECKING, Protocol, runtime_checkable

import numpy as np

from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocationResult,
    StreetCluster,
)

if TYPE_CHECKING:
    from openaddrbr.core._records import (
        AddressRecord,
        CityRecord,
        FullAddressRecord,
        GeoInfoRecord,
    )


@runtime_checkable
class GeocoderDB(Protocol):
    """Protocol for geocoder SQLite database access."""

    def get_city_info_from_db(self, city_name: str, state_code: str) -> "CityRecord | None": ...
    def is_multi_street_cep(self, cep: str) -> bool: ...
    def query_address_by_cep(self, zip_code: str, limit: int = 10) -> "list[AddressRecord]": ...
    def query_address_by_street_names(self, street_names: list[str], city_code: int) -> "list[AddressRecord]": ...
    def query_street_query(self, query_ids: list[int], city_code: int) -> list[str]: ...
    def query_full_address_by_street_id(self, street_id: int) -> "list[FullAddressRecord]": ...
    def query_geo_locations(self, street_id: int, number: int, limit: int = 3) -> "list[GeoInfoRecord]": ...


@runtime_checkable
class CityFinder(Protocol):
    """Protocol for finding city info by name and state."""

    def get_city_info(self, city_name: str, state_code: str) -> CityInfo | None: ...


@runtime_checkable
class StreetSearcher(Protocol):
    """Protocol for searching streets by CEP or vector."""

    def search_by_cep(
        self,
        zip_code: str,
        street_norm: str,
        neighborhood_norm: str,
    ) -> StreetCluster | None: ...

    def search_vector(
        self, embedding: np.ndarray, city_code: int, limit: int = 20
    ) -> list[str]: ...


@runtime_checkable
class GeoCoder(Protocol):
    """Protocol for full geocoding operations."""

    def geocode(
        self,
        street: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str | None = None,
        number: int = 0,
    ) -> GeoLocationResult | None: ...


@runtime_checkable
class BatchGeocoder(Protocol):
    """Protocol for batch geocoding operations."""

    def get_geo_info_batch(
        self,
        addresses: list[AddressRequest],
        batch_size: int = 16,
    ) -> list[GeoLocationResult | None]: ...
