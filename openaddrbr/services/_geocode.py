"""Geocode service - main geocoding implementation."""

import os
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocation,
    GeoLocationResult,
    NormalizedAddress,
    StreetCluster,
)
from openaddrbr.data import (
    check_data_exists,
    download_data,
    query_address_by_street_names,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
    search_vector as search_vector_index,
)
from openaddrbr.data._config import get_model_path
from openaddrbr.services._city import get_city_info as _get_city_info
from openaddrbr.services._cep import search_by_cep, is_multi_street_cep
from openaddrbr.utils import find_best_street_match, normalize_text, text_similarity

MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

# Thread limiting
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Get or create the sentence transformer model."""
    global _model
    if _model is None:
        model_path = get_model_path()
        if not model_path.exists():
            print(f"[MODEL] Downloading model to {model_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_model = SentenceTransformer(MODEL_NAME)
            tmp_model.save(str(model_path))
            print(f"[MODEL] Model saved to local path")
        _model = SentenceTransformer(str(model_path))
        _model.max_seq_length = 128
    return _model


def _encode_street(street_norm: str) -> np.ndarray | None:
    """Encode a single street name to vector."""
    if not street_norm:
        return None
    model = _get_model()
    return model.encode([street_norm], show_progress_bar=False)[0]


def _encode_streets_batch(street_norms: list[str], batch_size: int) -> list[np.ndarray]:
    """Batch encode street names."""
    if not street_norms:
        return []
    return _get_model().encode(
        street_norms, batch_size=batch_size, show_progress_bar=False
    )


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


def _fetch_clusters_by_street_names(
    street_names: list[str], city_code: int
) -> list[StreetCluster]:
    """Fetch and build street clusters from normalized street names."""
    if not street_names:
        return []
    rows = query_address_by_street_names(street_names, city_code)
    if not rows:
        return []

    clusters: list[StreetCluster] = []
    last_street_id = None
    for row in rows:
        sid = row.street_id
        if sid != last_street_id:
            clusters.append(StreetCluster(street_id=sid))
            last_street_id = sid
        current = clusters[-1]
        current.street_normalized.add(row.street_normalized)
        current.neighborhood_normalized.add(row.neighborhood_normalized)
    return clusters


def _search_by_embedding(
    city_code: int,
    embedding: np.ndarray,
    street_norm: str,
    neighborhood_norm: str,
) -> StreetCluster | None:
    """Search by complete address using vector search + exact SQL."""
    if embedding is None or street_norm is None:
        return None
    query_ids = search_vector_index(embedding, city_code, limit=20)
    if not query_ids:
        return None

    street_rows = query_street_query(query_ids, city_code)
    street_names = [row.street_normalized for row in street_rows]
    if not street_names:
        return None

    clusters = _fetch_clusters_by_street_names(street_names, city_code)
    if not clusters:
        return None
    return find_best_street_match(
        clusters, street_norm, neighborhood_norm, min_neighborhood_similarity=0
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
            cluster_data["neighborhoods"].add(
                (row.neighborhood_normalized, row.neighborhood_name)
            )
            if row.zip_code:
                cluster_data["zip_codes"].add(
                    (str(row.zip_code).zfill(8), row.id, row.source_type)
                )

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