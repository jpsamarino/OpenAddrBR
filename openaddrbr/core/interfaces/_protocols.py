"""Protocol definitions for structural subtyping."""

from typing import TYPE_CHECKING, Any, Iterable, Protocol, runtime_checkable

import numpy as np

from openaddrbr.core.models import (
    AddressInfo,
    AddressRequest,
    CityInfo,
    NeighborhoodInfo,
    SearchHit,
    StreetSegmentInfo,
)

if TYPE_CHECKING:
    from openaddrbr.core.models import (
        AddressRecord,
        CityRecord,
        FullAddressRecord,
        GeoInfoRecord,
    )


@runtime_checkable
class AddressDataStore(Protocol):
    """Protocol for address SQLite database access."""

    def get_city_info_from_db(self, city_name: str, state_code: str) -> "CityRecord | None": ...
    def is_multi_street_cep(self, cep: str) -> bool: ...
    def query_address_by_cep(self, zip_code: str, limit: int = 10) -> "list[AddressRecord]": ...
    def query_address_by_street_names(
        self, street_names: Iterable[str], city_code: int
    ) -> "list[AddressRecord]": ...
    def query_street_query(self, query_ids: Iterable[int]) -> list[str]: ...
    def query_full_address_by_street_id(self, street_id: int) -> "list[FullAddressRecord]": ...
    def query_geo_locations(
        self, street_id: int, number: int, limit: int = 3
    ) -> "list[GeoInfoRecord]": ...
    def query_streets_by_query_id(self, query_ids: Iterable[int]) -> list[StreetSegmentInfo]: ...


@runtime_checkable
class VectorIndexSearcher(Protocol):
    """Protocol for vector index search operations (usearch)."""

    def search_city_streets(
        self, city_code: int, embedding: np.ndarray, limit: int = 20
    ) -> list[int]: ...

    def get_city_street_index(self, city_code: int) -> Any | None: ...

    def clear(self) -> None: ...


@runtime_checkable
class TextIndexSearcher(Protocol):
    """Protocol for text index search operations (Tantivy)."""

    def search_cities(self, query_text: str, limit: int = 10) -> list[SearchHit]: ...
    def get_cities_batch(self, doc_addresses: list[int]) -> list[CityInfo | None]: ...
    def search_neighborhoods(
        self, query_text: str, city_code: int, limit: int = 10
    ) -> list[SearchHit]: ...
    def get_neighborhoods_batch(self, doc_addresses: list[int]) -> list[NeighborhoodInfo | None]: ...
    def get_query_ids_batch(self, doc_addresses: list[int]) -> list[int | None]: ...


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
    ) -> AddressInfo | None: ...


@runtime_checkable
class BatchGeocoder(Protocol):
    """Protocol for batch geocoding operations."""

    def get_geo_info_batch(
        self,
        addresses: list[AddressRequest],
        batch_size: int = 16,
    ) -> list[AddressInfo | None]: ...
