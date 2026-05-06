"""SQLite database connection management."""

import sqlite3
from functools import lru_cache
from typing import Optional

_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Get a lazy SQLite connection to sgeobr.db."""
    global _conn
    if _conn is None:
        from openaddrbr.data._config import get_sgeodb_path
        db_path = get_sgeodb_path()
        if not db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. "
                "Please download data using: python -m openaddrbr download"
            )
        _conn = sqlite3.connect(db_path)
        _conn.row_factory = sqlite3.Row
    return _conn


def close_connection() -> None:
    """Close the database connection."""
    global _conn
    if _conn:
        _conn.close()
        _conn = None


@lru_cache(maxsize=7000)
def get_city_info_from_db(city_name: str, state_code: str):
    """Query city info from database. Cached."""
    from openaddrbr.utils import normalize_text

    conn = get_connection()
    state = state_code.strip().upper()
    target = normalize_text(city_name)

    query = """
        SELECT city_code, city_name, state_code FROM cities
        WHERE state_code = ?
          AND city_normalized = ?
        LIMIT 1
    """
    row = conn.execute(query, (state, target)).fetchone()
    return row


@lru_cache(maxsize=10000)
def is_multi_street_cep(cep: str) -> bool:
    """Check if CEP has multiple streets. Cached."""
    conn = get_connection()
    query = "SELECT 1 FROM multi_street_ceps WHERE zip_code = ? LIMIT 1"
    result = conn.execute(query, (cep,)).fetchone()
    return result is not None


def query_address_by_cep(zip_code: str, limit: int = 10):
    """Query address rows by zip code."""
    conn = get_connection()
    query = """
        SELECT street_id, street_normalized, neighborhood_normalized
        FROM address
        WHERE zip_code = ?
        ORDER BY street_id, id DESC
        LIMIT ?
    """
    return conn.execute(query, (zip_code, limit)).fetchall()


def query_address_by_street_names(street_names: list[str], city_code: int):
    """Query address rows by street names."""
    if not street_names:
        return []
    conn = get_connection()
    placeholders = ", ".join("?" * len(street_names))
    query = f"""
        SELECT street_id, street_normalized, neighborhood_normalized
        FROM address
        WHERE city_code = ?
          AND street_normalized IN ({placeholders})
        ORDER BY street_id, qt_refs DESC
    """
    return conn.execute(query, [city_code] + street_names).fetchall()


def query_full_address_by_street_id(street_id: int):
    """Query full address info by street_id."""
    conn = get_connection()
    query = """
        SELECT
            street_name, street_normalized,
            neighborhood_name, neighborhood_normalized,
            zip_code, id, source_type
        FROM address
        WHERE street_id = ?
        ORDER BY qt_refs DESC
    """
    return conn.execute(query, (street_id,)).fetchall()


def query_geo_locations(street_id: int, number: int, limit: int = 3):
    """Query geo locations for a street_id."""
    conn = get_connection()
    number = number if number is not None and number < 999999 else 0
    query = """
        SELECT latitude, longitude, address_number, address_id
        FROM geo_locations
        WHERE street_id = ?
        ORDER BY ABS(CAST(address_number AS INTEGER) - ?)
        LIMIT ?
    """
    return conn.execute(query, (street_id, number, limit)).fetchall()


def query_street_query(query_ids: list[int], city_code: int):
    """Query street_query table for vector search results."""
    if not query_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(query_ids))
    query = f"""
        SELECT DISTINCT street_normalized
        FROM street_query
        WHERE query_id IN ({placeholders}) AND city_code = ?
    """
    return conn.execute(query, query_ids + [str(city_code)]).fetchall()


def query_query_ids(city_code: int) -> list[int]:
    """Query all query_ids for a city."""
    conn = get_connection()
    query = "SELECT DISTINCT query_id FROM street_query WHERE city_code = ? LIMIT 200"
    return [row[0] for row in conn.execute(query, (str(city_code),)).fetchall()]