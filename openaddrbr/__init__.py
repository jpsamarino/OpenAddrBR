"""OpenAddrBR - Brazilian address geocoder using vector search."""

from openaddrbr.core._geocoder import Geocoder
from openaddrbr.core.models import AddressInfo, AddressRequest, CityInfo, NeighborhoodInfo

__all__ = ["Geocoder", "geocode", "get_geo_info_batch", "NeighborhoodInfo"]


# Lazy-initialized default geocoder instance for backwards-compatible function API
_default_geocoder: Geocoder | None = None


def geocode(
    street: str,
    neighborhood: str,
    city: str,
    state: str,
    zip_code: str | None = None,
    number: int = 0,
) -> AddressInfo | None:
    """Geocode an address to lat/long coordinates (function-style API)."""
    global _default_geocoder
    if _default_geocoder is None:
        _default_geocoder = Geocoder()
    return _default_geocoder.geocode(street, neighborhood, city, state, zip_code, number)


def get_geo_info_batch(
    addresses: list[AddressRequest],
    batch_size: int = 16,
) -> list[AddressInfo | None]:
    """Geocode multiple addresses in batch (function-style API)."""
    global _default_geocoder
    if _default_geocoder is None:
        _default_geocoder = Geocoder()
    return _default_geocoder.geocode_batch(addresses, batch_size)
