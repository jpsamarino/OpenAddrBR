"""
OpenAddrBR - Brazilian address geocoder using vector search.

Usage:
    from openaddrbr import geocode

    result = geocode(
        street="Rua das Flores",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01310000",
        number=100
    )
"""

from openaddrbr.services import get_city_info, search_by_cep, geocode, get_geo_info_batch
from openaddrbr.data import set_data_path, get_data_path, download_data

__all__ = [
    "geocode",
    "get_city_info",
    "search_by_cep",
    "get_geo_info_batch",
    "set_data_path",
    "get_data_path",
    "download_data",
]