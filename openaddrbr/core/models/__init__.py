"""Core models package."""

from openaddrbr.core.models._db_models import (
    AddressRecord,
    CityRecord,
    FullAddressRecord,
    GeoInfoRecord,
)
from openaddrbr.core.models._models import (
    AddressInfo,
    AddressRequest,
    CityCore,
    CityInfo,
    GeoLocation,
    NeighborhoodInfo,
    NormalizedAddress,
    SearchHit,
    StreetCluster,
    StreetInfo,
    StreetSegmentInfo,
)

__all__ = [
    # DB records
    "CityRecord",
    "AddressRecord",
    "FullAddressRecord",
    "GeoInfoRecord",
    # Domain models
    "StreetCluster",
    "StreetSegmentInfo",
    "CityCore",
    "CityInfo",
    "NeighborhoodInfo",
    "StreetInfo",
    "AddressInfo",
    "GeoLocation",
    "NormalizedAddress",
    "AddressRequest",
    "SearchHit",
]
