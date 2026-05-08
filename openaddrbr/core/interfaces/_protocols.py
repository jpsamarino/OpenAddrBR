"""Protocol definitions for structural subtyping."""

from typing import Protocol, runtime_checkable

import numpy as np

from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocationResult,
    StreetCluster,
)


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
