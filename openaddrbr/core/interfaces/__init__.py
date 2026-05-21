"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    BatchGeocoder,
    GeoCoder,
    GeocoderDB,
)

__all__ = [
    "GeocoderDB",
    "GeoCoder",
    "BatchGeocoder",
]