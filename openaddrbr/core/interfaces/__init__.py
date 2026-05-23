"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    AddressDataStore,
    BatchGeocoder,
    GeoCoder,
    TextIndexSearcher,
    VectorIndexSearcher,
)

__all__ = [
    "AddressDataStore",
    "GeoCoder",
    "BatchGeocoder",
    "TextIndexSearcher",
    "VectorIndexSearcher",
]