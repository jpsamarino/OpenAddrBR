"""Data package - path configuration and vector search."""

from openaddrbr.core._database import Database
from openaddrbr.core._env import (
    get_data_path,
    get_model_path,
    get_sgeodb_path,
    get_usearch_dir,
    set_data_path,
)
from openaddrbr.data._hf_downloader import check_data_exists, download_data
from openaddrbr.data._usearch import get_semantic_index, search_vector

__all__ = [
    "get_data_path",
    "set_data_path",
    "get_sgeodb_path",
    "get_usearch_dir",
    "get_model_path",
    "check_data_exists",
    "download_data",
    "get_semantic_index",
    "search_vector",
    "query_street_query",
]


# Lazy-initialized database instance
_db: Database | None = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db


def query_street_query(query_ids: list[int]) -> list[str]:
    """Query street normalized names by query IDs."""
    return _get_db().query_street_query(query_ids)
