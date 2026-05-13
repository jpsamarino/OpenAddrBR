"""Database record types - shared between Database and its Protocol."""

from typing import NamedTuple


class CityRecord(NamedTuple):
    city_code: int
    city_name: str
    state_code: str


class AddressRecord(NamedTuple):
    street_id: int
    street_normalized: str
    neighborhood_normalized: str


class FullAddressRecord(NamedTuple):
    street_name: str
    street_normalized: str
    neighborhood_name: str
    neighborhood_normalized: str
    zip_code: str
    id: int
    source_type: str


class GeoInfoRecord(NamedTuple):
    latitude: float
    longitude: float
    address_number: int
    address_id: int
