"""City info service - get_city_info implementation."""

from openaddrbr.core.interfaces._protocols import GeocoderDB
from openaddrbr.core.models import CityInfo


def get_city_info(city: str, state: str, db: GeocoderDB | None = None) -> CityInfo | None:
    """Get city info by name and state.

    Args:
        city: City name
        state: State code (e.g., "SP")
        db: Database instance (optional for backward compat)
    """
    if db is None:
        # Fallback for backward compat during transition
        from openaddrbr.core._database import Database

        db = Database()

    record = db.get_city_info_from_db(city, state)
    if not record:
        return None
    return CityInfo(
        city_code=record.city_code,
        city_name=record.city_name,
        state_code=record.state_code,
    )
