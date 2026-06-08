"""Domain models for OpenAddrBR."""

from dataclasses import dataclass, field
from typing import NamedTuple


class SearchHit(NamedTuple):
    """A search hit from TextSearchEngine — score and doc address."""

    score: float
    doc_address: int


@dataclass(slots=True)
class StreetCluster:
    """Group of address variations grouped by street_id for matching."""

    street_id: int
    street_normalized: set[str] = field(default_factory=set)
    neighborhood_normalized: set[str] = field(default_factory=set)


class CityCore(NamedTuple):
    """City information (internal model, no coordinates)."""

    city_code: int
    city_name: str
    state_code: str


@dataclass
class CityInfo:
    """City information with reference coordinates (search output)."""

    # remove city_normalized?
    city_code: int
    city_name: str
    city_normalized: str
    state_code: str
    latitude: float
    longitude: float


@dataclass
class NeighborhoodInfo:
    """Neighborhood information with reference coordinates (search output)."""

    # remove neighborhood_normalized?
    neighborhood_name: str
    neighborhood_normalized: str
    city_code: int
    latitude: float
    longitude: float


@dataclass
class StreetInfo:
    """Street information (search output)."""

    # remove street_normalized and neighborhood_normalized, add latitude and longitude
    street_id: int
    street_name: str
    street_normalized: str
    city_code: int
    zip_codes: list[str]
    neighborhood_name: str | None = None
    neighborhood_normalized: str | None = None


@dataclass
class StreetSegmentInfo:
    """Street segment with reference coordinates (search output).

    Aggregates multiple zip_codes for same street+neighborhood when 'A' rows
    only add CEP variations. 'A' rows with different street names are only
    added if that street_normalized hasn't been seen before.
    """

    street_id: int
    street_name: str
    street_normalized: str
    neighborhood_name: str
    neighborhood_normalized: str
    zip_codes: list[str]
    latitude: float
    longitude: float


@dataclass
class AddressInfo:
    """Result of a geocoding operation."""

    lat: float
    long: float
    street_name: str
    neighborhood: str
    city: str
    state: str
    zip_code: str
    number: int
    ref_number_lat_long: int
    address: str = ""


class GeoLocation(NamedTuple):
    """Geo location result."""

    address_id: int
    latitude: float
    longitude: float
    address_number: int


@dataclass(slots=True)
class AddressRequest:
    """Address request model for geocoding."""

    city: str
    state: str
    street: str = ""
    neighborhood: str = ""
    zip_code: str | None = None
    street_number: int = 0


class NormalizedAddress(NamedTuple):
    """Normalized address data used in batch processing."""

    order: int
    address: AddressRequest
    city_info: CityInfo | None
    street_norm: str
    neighborhood_norm: str
    zip_code: str | None
    number: int
