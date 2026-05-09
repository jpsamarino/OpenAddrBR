"""Compatibility shim - re-export domain models."""

from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocation,
    GeoLocationResult,
    NormalizedAddress,
    StreetCluster,
)

__all__ = [
    "StreetCluster",
    "CityInfo",
    "GeoLocation",
    "NormalizedAddress",
    "AddressRequest",
    "GeoLocationResult",
]
