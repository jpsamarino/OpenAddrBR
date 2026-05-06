"""Sync implementation of ISGEODatabase backed by SQLite."""

from openaddrbr.data import (
    get_connection,
    get_city_info_from_db,
    is_multi_street_cep as _is_multi_street_cep,
    query_address_by_cep,
    query_address_by_street_names,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
)


class SGEODatabaseSync:
    """Synchronous implementation of ISGEODatabase using direct DB calls."""

    def __init__(self):
        self._conn = None

    def initialize(self) -> None:
        """Initialize the database connection."""
        self._conn = get_connection()

    def close(self) -> None:
        """Close the database connection."""
        from openaddrbr.data import close_connection
        close_connection()
        self._conn = None

    def get_city_info(self, city_name: str, state_code: str) -> tuple | None:
        """Get city info by name and state code."""
        row = get_city_info_from_db(city_name, state_code)
        if row is None:
            return None
        return (row["city_code"], row["city_name"], row["state_code"])

    def is_multi_street_cep(self, cep: str) -> bool:
        """Check if CEP has multiple streets."""
        return _is_multi_street_cep(cep)

    def fetch_address_by_cep(self, zip_code: str, limit: int = 10) -> list[tuple]:
        """Fetch address rows by zip code."""
        rows = query_address_by_cep(zip_code, limit=limit)
        return [tuple(row) for row in rows]

    def fetch_address_by_street_id(self, street_id: int) -> list[tuple]:
        """Fetch address rows by street ID."""
        rows = query_full_address_by_street_id(street_id)
        return [tuple(row) for row in rows]

    def fetch_geo_location(self, street_id: int, number: int, limit: int = 3) -> list[tuple]:
        """Fetch geo locations for a street."""
        rows = query_geo_locations(street_id, number, limit=limit)
        return [tuple(row) for row in rows]

    def fetch_street_by_query_ids(self, query_ids: list[int], city_code: int) -> list[str]:
        """Fetch street info by query IDs."""
        rows = query_street_query(query_ids, city_code)
        return [row["street_normalized"] for row in rows]

    def fetch_address_by_street_names(self, street_names: list[str], city_code: int) -> list[tuple]:
        """Fetch address rows by street names."""
        rows = query_address_by_street_names(street_names, city_code)
        return [tuple(row) for row in rows]

    def fetch_query_ids(self, city_code: int) -> list[int]:
        """Fetch all query IDs for a city."""
        conn = get_connection()
        rows = conn.execute(
            "SELECT query_id FROM street_query WHERE city_code = ?",
            (str(city_code),)
        ).fetchall()
        return [row["query_id"] for row in rows]