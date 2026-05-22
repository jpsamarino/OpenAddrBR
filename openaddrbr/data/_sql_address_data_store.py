"""SQLite database — thread-safe connection pool with bounded LRU caches."""

import array
import threading
from pathlib import Path

import apsw
from cachetools import LRUCache

from openaddrbr.core.env import get_default_data_path, get_sgeodb_path
from openaddrbr.core.interfaces import AddressDataStore
from openaddrbr.core.models import (
    AddressRecord,
    CityRecord,
    FullAddressRecord,
    GeoInfoRecord,
)
from openaddrbr.utils import normalize_text


class SqlAddressDataStore(AddressDataStore):
    """Thread-safe database accessor with connection pooling and bounded caches.

    Args:
        data_path: Path to data directory. Defaults to env var or package default.
    """

    def __init__(self, data_path: str | Path | None = None):
        if data_path is None:
            data_path = get_default_data_path()
        self._db_path = str(get_sgeodb_path(Path(data_path)))
        self._lock = threading.Lock()
        self._cursors: dict[int, apsw.Cursor] = {}
        self._conn = None

        # Bounded caches (LRUCache replaces old @lru_cache decorators)
        self._city_cache = LRUCache(maxsize=7000)
        self._multi_street_cache = LRUCache(maxsize=10000)

    def _get_conn(self) -> apsw.Connection:
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = apsw.Connection(
                        self._db_path,
                        flags=apsw.SQLITE_OPEN_READONLY | apsw.SQLITE_OPEN_NOMUTEX,
                    )
                    self._conn.execute("PRAGMA cache_size = -64000")
                    self._conn.execute("PRAGMA mmap_size = 134217728")
                    self._conn.execute("PRAGMA temp_store = MEMORY")
                    self._conn.execute("PRAGMA query_only = ON")
        return self._conn

    def _get_cursor(self) -> apsw.Cursor:
        tid = threading.get_ident()
        if tid not in self._cursors:
            self._cursors[tid] = self._get_conn().cursor()
        return self._cursors[tid]

    def close(self) -> None:
        with self._lock:
            self._cursors.clear()
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # ---- Query methods ----

    def get_city_info_from_db(self, city_name: str, state_code: str) -> CityRecord | None:
        key = (city_name, state_code.upper().strip())
        if key in self._city_cache:
            return self._city_cache[key]

        cursor = self._get_cursor()
        target = normalize_text(city_name)
        cursor.execute(
            "SELECT city_code, city_name, state_code FROM cities "
            "WHERE state_code = ? AND city_normalized = ? LIMIT 1",
            (state_code.strip().upper(), target),
        )
        row = cursor.fetchone()
        if not row:
            return None
        record = CityRecord(*row)
        self._city_cache[key] = record
        return record

    def is_multi_street_cep(self, cep: str) -> bool:
        if cep in self._multi_street_cache:
            return self._multi_street_cache[cep]
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT 1 FROM multi_street_ceps WHERE zip_code = ? LIMIT 1",
            (cep,),
        )
        result = cursor.fetchone() is not None
        self._multi_street_cache[cep] = result
        return result

    def query_address_by_cep(self, zip_code: str, limit: int = 10) -> list[AddressRecord]:
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT street_id, street_normalized, neighborhood_normalized "
            "FROM address WHERE zip_code = ? ORDER BY street_id, id DESC LIMIT ?",
            (zip_code, limit),
        )
        return [AddressRecord(*r) for r in cursor.fetchall()]

    def query_address_by_street_names(
        self, street_names: list[str], city_code: int
    ) -> list[AddressRecord]:
        if not street_names:
            return []
        cursor = self._get_cursor()
        placeholders = ", ".join("?" * len(street_names))
        cursor.execute(
            f"SELECT street_id, street_normalized, neighborhood_normalized "
            f"FROM address WHERE city_code = ? "
            f"AND street_normalized IN ({placeholders}) "
            f"ORDER BY street_id, qt_refs DESC",
            [city_code] + street_names,
        )
        return [AddressRecord(*r) for r in cursor.fetchall()]

    def query_full_address_by_street_id(self, street_id: int) -> list[FullAddressRecord]:
        cursor = self._get_cursor()
        cursor.execute(
            "SELECT street_name, street_normalized, neighborhood_name, "
            "neighborhood_normalized, zip_code, id, source_type "
            "FROM address WHERE street_id = ? ORDER BY qt_refs DESC",
            (street_id,),
        )
        return [FullAddressRecord(*r) for r in cursor.fetchall()]

    def query_geo_locations(
        self, street_id: int, number: int, limit: int = 3
    ) -> list[GeoInfoRecord]:
        cursor = self._get_cursor()
        n = number if number is not None and number < 999999 else 0
        cursor.execute(
            "SELECT latitude, longitude, address_number, address_id "
            "FROM geo_locations WHERE street_id = ? "
            "ORDER BY ABS(CAST(address_number AS INTEGER) - ?) LIMIT ?",
            (street_id, n, limit),
        )
        return [GeoInfoRecord(*r) for r in cursor.fetchall()]

    def query_street_query(self, query_ids: list[int]) -> list[str]:
        if not query_ids:
            return []
        cursor = self._get_cursor()
        q_arr = array.array("q", query_ids)
        cursor.execute(
            "SELECT street_normalized FROM street_query WHERE query_id IN carray(?)",
            (apsw.carray(q_arr, flags=apsw.SQLITE_CARRAY_INT64),),
        )
        return [r[0] for r in cursor.fetchall()]
