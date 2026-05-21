"""Data package - path configuration and vector search."""

from openaddrbr.core._env import (
    get_data_path,
    get_model_path,
    get_sgeodb_path,
    get_usearch_dir,
    set_data_path,
)
from openaddrbr.data._data_download import check_data_exists, download_data
from openaddrbr.data._sql_db import SQLDB
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.data._usearch import UsearchIndex, get_semantic_index, search_vector

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
    "UsearchIndex",
    "SQLDB",
    "TantivySearch",
]