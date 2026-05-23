"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    AddressDataStore,
    BatchGeocoder,
    GeoCoder,
    VectorIndexSearcher,
)

__all__ = [
    "AddressDataStore",
    "GeoCoder",
    "BatchGeocoder",
    "VectorIndexSearcher",
]