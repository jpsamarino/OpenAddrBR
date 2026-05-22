"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    AddressDataStore,
    BatchGeocoder,
    GeoCoder,
)

__all__ = [
    "AddressDataStore",
    "GeoCoder",
    "BatchGeocoder",
]