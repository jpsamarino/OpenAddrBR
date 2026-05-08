"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    BatchGeocoder,
    CityFinder,
    GeoCoder,
    StreetSearcher,
)

__all__ = [
    "CityFinder",
    "StreetSearcher",
    "GeoCoder",
    "BatchGeocoder",
]
