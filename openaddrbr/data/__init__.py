"""Data package - path configuration and vector search."""

from openaddrbr.core._env import (
    get_data_path,
    get_model_path,
    get_sgeodb_path,
    get_tantivy_dir,
    get_usearch_dir,
    set_data_path,
)
from openaddrbr.data._data_download import check_data_exists, download_data
from openaddrbr.data._sql_search import SqlSearchEngine
from openaddrbr.data._text_search import TextSearchEngine
from openaddrbr.data._vector_search import VectorSearchEngine

__all__ = [
    "SqlSearchEngine",
    "TextSearchEngine",
    "VectorSearchEngine",
    "check_data_exists",
    "download_data",
    "get_data_path",
    "get_model_path",
    "get_sgeodb_path",
    "get_tantivy_dir",
    "get_usearch_dir",
    "set_data_path",
]