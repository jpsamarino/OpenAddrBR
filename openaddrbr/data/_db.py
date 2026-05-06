"""APSW-based database connection management with optimized settings and connection pooling."""

import array
import threading
from functools import lru_cache
from typing import Optional

import apsw

from openaddrbr.data._config import get_sgeodb_path
from typing import NamedTuple


class CityRecord(NamedTuple):
    """Record for city queries: (city_code, city_name, state_code)."""
    city_code: int
    city_name: str
    state_code: str


class AddressRecord(NamedTuple):
    """Record for address queries by CEP or street names: (street_id, street_normalized, neighborhood_normalized)."""
    street_id: int
    street_normalized: str
    neighborhood_normalized: str


class FullAddressRecord(NamedTuple):
    """Record for full address queries: (street_name, street_normalized, neighborhood_name, neighborhood_normalized, zip_code, id, source_type)."""
    street_name: str
    street_normalized: str
    neighborhood_name: str
    neighborhood_normalized: str
    zip_code: str
    id: int
    source_type: str


class GeoInfoRecord(NamedTuple):
    """Record for geo location queries: (latitude, longitude, address_number, address_id)."""
    latitude: float
    longitude: float
    address_number: int
    address_id: int


# ----- Global singleton instance -----
class _DB:
    """Database accessor with connection pooling and cursor reuse per thread."""

    def __init__(self):
        self._db_path = str(get_sgeodb_path())
        self._lock = threading.Lock()
        self._cursors: dict[int, apsw.Cursor] = {}
        self._conn: Optional[apsw.Connection] = None

    def _get_conn(self) -> apsw.Connection:
        """Get or create the connection."""
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = apsw.Connection(
                        self._db_path,
                        flags=apsw.SQLITE_OPEN_READONLY | apsw.SQLITE_OPEN_NOMUTEX
                    )
                    self._conn.execute("PRAGMA cache_size = -64000")
                    self._conn.execute("PRAGMA mmap_size = 134217728")
                    self._conn.execute("PRAGMA temp_store = MEMORY")
                    self._conn.execute("PRAGMA query_only = ON")
        return self._conn

    def _get_cursor(self) -> apsw.Cursor:
        """Get a thread-local cursor, reusing if available."""
        tid = threading.get_ident()
        if tid not in self._cursors:
            self._cursors[tid] = self._get_conn().cursor()
        return self._cursors[tid]

    def close(self) -> None:
        """Close the connection."""
        with self._lock:
            self._cursors.clear()
            if self._conn is not None:
                self._conn.close()
                self._conn = None


# Global singleton
_db_instance: Optional[_DB] = None


def _get_db() -> _DB:
    """Get the global DB instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = _DB()
    return _db_instance


def close_connection() -> None:
    """Close the database connection."""
    _get_db().close()


def get_connection():
    """Backward-compatible alias. Returns the connection (not typically needed)."""
    return _get_db()._get_conn()


# ----- Query functions -----

@lru_cache(maxsize=7000)
def get_city_info_from_db(city_name: str, state_code: str) -> CityRecord | None:
    """Query city info from database. Cached."""
    from openaddrbr.utils import normalize_text

    cursor = _get_db()._get_cursor()
    state = state_code.strip().upper()
    target = normalize_text(city_name)

    cursor.execute(
        "SELECT city_code, city_name, state_code FROM cities "
        "WHERE state_code = ? AND city_normalized = ? LIMIT 1",
        (state, target),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return CityRecord(*row)


@lru_cache(maxsize=10000)
def is_multi_street_cep(cep: str) -> bool:
    """Check if CEP has multiple streets. Cached."""
    cursor = _get_db()._get_cursor()
    cursor.execute(
        "SELECT 1 FROM multi_street_ceps WHERE zip_code = ? LIMIT 1",
        (cep,),
    )
    return cursor.fetchone() is not None


def query_address_by_cep(zip_code: str, limit: int = 10) -> list[AddressRecord]:
    """Query address rows by zip code."""
    cursor = _get_db()._get_cursor()
    cursor.execute(
        "SELECT street_id, street_normalized, neighborhood_normalized "
        "FROM address WHERE zip_code = ? ORDER BY street_id, id DESC LIMIT ?",
        (zip_code, limit),
    )
    return [AddressRecord(*r) for r in cursor.fetchall()]


def query_address_by_street_names(street_names: list[str], city_code: int) -> list[AddressRecord]:
    """Query address rows by street names."""
    if not street_names:
        return []
    cursor = _get_db()._get_cursor()
    placeholders = ", ".join("?" * len(street_names))
    cursor.execute(
        f"SELECT street_id, street_normalized, neighborhood_normalized "
        f"FROM address WHERE city_code = ? "
        f"AND street_normalized IN ({placeholders}) "
        f"ORDER BY street_id, qt_refs DESC",
        [city_code] + street_names,
    )
    return [AddressRecord(*r) for r in cursor.fetchall()]


def query_full_address_by_street_id(street_id: int) -> list[FullAddressRecord]:
    """Query full address info by street_id."""
    cursor = _get_db()._get_cursor()
    cursor.execute(
        "SELECT street_name, street_normalized, neighborhood_name, "
        "neighborhood_normalized, zip_code, id, source_type "
        "FROM address WHERE street_id = ? ORDER BY qt_refs DESC",
        (street_id,),
    )
    return [FullAddressRecord(*r) for r in cursor.fetchall()]


def query_geo_locations(street_id: int, number: int, limit: int = 3) -> list[GeoInfoRecord]:
    """Query geo locations for a street_id."""
    cursor = _get_db()._get_cursor()
    n = number if number is not None and number < 999999 else 0
    cursor.execute(
        "SELECT latitude, longitude, address_number, address_id "
        "FROM geo_locations WHERE street_id = ? "
        "ORDER BY ABS(CAST(address_number AS INTEGER) - ?) LIMIT ?",
        (street_id, n, limit),
    )
    return [GeoInfoRecord(*r) for r in cursor.fetchall()]


def query_street_query(query_ids: list[int], city_code: int) -> list[str]:
    """Query street_query table for vector search results."""
    if not query_ids:
        return []
    cursor = _get_db()._get_cursor()
    q_arr = array.array('q', query_ids)
    cursor.execute(
        "SELECT DISTINCT street_normalized FROM street_query "
        "WHERE query_id IN carray(?) AND city_code = ?",
        (apsw.carray(q_arr, flags=apsw.SQLITE_CARRAY_INT64), str(city_code)),
    )
    return [r[0] for r in cursor.fetchall()]


def query_query_ids(city_code: int) -> list[int]:
    """Query all query_ids for a city."""
    cursor = _get_db()._get_cursor()
    cursor.execute(
        "SELECT DISTINCT query_id FROM street_query WHERE city_code = ? LIMIT 200",
        (str(city_code),),
    )
    return [row[0] for row in cursor.fetchall()]
