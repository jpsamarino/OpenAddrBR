"""Data package - database, usearch, and download management."""

from openaddrbr.data._config import (
    get_data_path,
    set_data_path,
    get_sgeodb_path,
    get_usearch_dir,
    get_model_path,
)
from openaddrbr.data._db import (
    get_connection,
    close_connection,
    get_city_info_from_db,
    is_multi_street_cep,
    query_address_by_cep,
    query_address_by_street_names,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
    query_query_ids,
)
from openaddrbr.data._usearch import get_semantic_index, search_vector
from openaddrbr.data._hf_downloader import download_data, check_data_exists

__all__ = [
    "get_data_path",
    "set_data_path",
    "get_sgeodb_path",
    "get_usearch_dir",
    "get_model_path",
    "get_connection",
    "close_connection",
    "get_city_info_from_db",
    "is_multi_street_cep",
    "query_address_by_cep",
    "query_address_by_street_names",
    "query_full_address_by_street_id",
    "query_geo_locations",
    "query_street_query",
    "query_query_ids",
    "get_semantic_index",
    "search_vector",
    "download_data",
    "check_data_exists",
]
