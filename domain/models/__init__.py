"""Compatibility shim - re-export domain models."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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