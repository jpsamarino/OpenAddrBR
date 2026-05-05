"""City service - get_city_info implementation."""

from functools import lru_cache

from openaddrbr.core.models import CityInfo
from openaddrbr.data import get_city_info_from_db


@lru_cache(maxsize=7000)
def get_city_info(city_name: str, state_code: str) -> CityInfo | None:
    """Get IBGE city info from city name and state code."""
    row = get_city_info_from_db(city_name, state_code)
    if not row:
        return None

    return CityInfo(
        city_code=row["city_code"],
        city_name=row["city_name"],
        state_code=row["state_code"],
    )