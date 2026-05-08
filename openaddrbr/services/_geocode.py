"""Geocode service - main geocoding implementation."""

from openaddrbr.core.models import (
    CityInfo,
    GeoLocation,
    GeoLocationResult,
    StreetCluster,
)
from openaddrbr.data import (
    check_data_exists,
    download_data,
    query_full_address_by_street_id,
    query_geo_locations,
)
from openaddrbr.services._city import get_city_info as _get_city_info
from openaddrbr.services._cep import search_by_cep, is_multi_street_cep
from openaddrbr.services._encoder import _encode_street
from openaddrbr.services._vector_search import _search_by_embedding
from openaddrbr.utils import normalize_text, text_similarity


def _find_best_geo_location(
    street_id: int, number: int, limit_numbers: int = 3
) -> GeoLocation | None:
    """Find best geo location for street_id and number with parity matching."""
    rows = query_geo_locations(street_id, number, limit_numbers)

    if not rows:
        return None

    ref_is_even = number % 2 == 0

    for row in rows:
        addr_num = row.address_number
        if addr_num is None:
            continue
        try:
            addr_int = int(addr_num)
        except (ValueError, TypeError):
            continue

        addr_is_even = addr_int % 2 == 0
        if ref_is_even == addr_is_even:
            return GeoLocation(
                latitude=row.latitude,
                longitude=row.longitude,
                address_id=row.address_id,
                address_number=addr_num,
            )

    # No parity match - return first
    row = rows[0]
    return GeoLocation(
        latitude=row.latitude,
        longitude=row.longitude,
        address_id=row.address_id,
        address_number=int(row.address_number),
    )


def _build_result(
    street_cluster: StreetCluster,
    street: str,
    street_norm: str,
    neighborhood_norm: str,
    cep: str | None,
    number: int,
    city_info: CityInfo,
) -> GeoLocationResult | None:
    """Build GeoLocationResult from street_cluster."""
    street_id = street_cluster.street_id
    rows = query_full_address_by_street_id(street_id)

    if not rows:
        return None

    cluster_data = {"streets": set(), "neighborhoods": set(), "zip_codes": set()}

    for row in rows:
        if row.street_normalized in street_cluster.street_normalized:
            cluster_data["streets"].add((row.street_normalized, row.street_name))
            cluster_data["neighborhoods"].add((row.neighborhood_normalized, row.neighborhood_name))
            if row.zip_code:
                cluster_data["zip_codes"].add((str(row.zip_code).zfill(8), row.id, row.source_type))

    geo_result = _find_best_geo_location(street_id, number)
    if geo_result:
        address_id_ref_lat_long = geo_result.address_id
        lat = geo_result.latitude
        long = geo_result.longitude
        number_ref = geo_result.address_number
    else:
        lat, long = 0.0, 0.0
        number_ref = 0
        address_id_ref_lat_long = None

    # Find best matching street
    best_street = (0, "")
    for s_norm, s_accents in cluster_data["streets"]:
        if s_accents == street:
            best_street = (1, s_accents)
            break
        sim = text_similarity(street_norm, s_norm)
        if sim > best_street[0]:
            best_street = (sim, s_accents)

    # Find best matching neighborhood
    best_neighborhood = (0, "")
    for n_norm, n in cluster_data["neighborhoods"]:
        sim = text_similarity(neighborhood_norm, n_norm)
        if sim > best_neighborhood[0]:
            best_neighborhood = (sim, n)

    # Find best matching zip code
    best_zip_code = (0, "")
    if cep:
        for z, _, _ in cluster_data["zip_codes"]:
            sim = text_similarity(cep, z)
            if sim > best_zip_code[0]:
                best_zip_code = (sim, z)
    else:
        for z in cluster_data["zip_codes"]:
            if address_id_ref_lat_long and z[1] == address_id_ref_lat_long:
                if best_zip_code[1] == "" or z[2] == "A":
                    best_zip_code = (1.0, z[0])

    addr_full = f"{best_street[1]}, {number}, {best_neighborhood[1]}, {city_info.city_name} - {city_info.state_code}, {best_zip_code[1]}"

    return GeoLocationResult(
        lat=lat,
        long=long,
        street_name=best_street[1],
        neighborhood=best_neighborhood[1],
        city=city_info.city_name,
        state=city_info.state_code,
        number=number,
        ref_number_lat_long=number_ref if number_ref else 0,
        zip_code=best_zip_code[1],
        address=addr_full,
    )


def geocode(
    street: str,
    neighborhood: str,
    city: str,
    state: str,
    zip_code: str | None = None,
    number: int = 0,
) -> GeoLocationResult | None:
    """Geocode an address to lat/long coordinates."""
    # Auto-download data if not present
    if not check_data_exists():
        print("Data not found. Downloading from Hugging Face...")
        download_data()

    city_info = _get_city_info(city, state)
    if not city_info:
        return None

    street_norm = normalize_text(street) if street else ""
    neighborhood_norm = normalize_text(neighborhood) if neighborhood else ""

    clean_zip = None
    if zip_code:
        clean_zip = "".join(c for c in str(zip_code) if c.isdigit()).zfill(8)

    # 1. Try CEP search first (if not multi-street), fall back to address search
    street_cluster = None
    if clean_zip and not is_multi_street_cep(clean_zip):
        street_cluster = search_by_cep(clean_zip, street_norm, neighborhood_norm)

    if not street_cluster:
        embedding = _encode_street(street_norm)
        street_cluster = _search_by_embedding(
            city_info.city_code, embedding, street_norm, neighborhood_norm
        )

    if street_cluster:
        return _build_result(
            street_cluster,
            street,
            street_norm,
            neighborhood_norm,
            clean_zip,
            number,
            city_info,
        )

    return None
