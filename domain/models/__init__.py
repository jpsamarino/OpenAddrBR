"""Compatibility shim - re-export domain models."""

from openaddrbr.core.models import (
    StreetCluster,
    CityInfo,
    GeoLocation,
    NormalizedAddress,
    AddressRequest,
    GeoLocationResult,
)

__all__ = [
    "StreetCluster",
    "CityInfo",
    "GeoLocation",
    "NormalizedAddress",
    "AddressRequest",
    "GeoLocationResult",
]