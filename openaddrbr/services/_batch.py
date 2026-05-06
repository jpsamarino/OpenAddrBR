"""Batch geocoding service - get_geo_info_batch implementation."""

from openaddrbr.core.models import AddressRequest, GeoLocationResult, NormalizedAddress, StreetCluster
from openaddrbr.services._geocode import (
    _encode_streets_batch,
    _build_result,
    _search_by_embedding,
    _get_city_info,
    _fetch_clusters_by_street_names,
    is_multi_street_cep,
    search_by_cep,
)
from openaddrbr.utils import normalize_text, find_best_street_match
from openaddrbr.data import query_street_query, search_vector as search_vector_index


def get_geo_info_batch(
    addresses: list[AddressRequest],
    batch_size: int = 16,
) -> list[GeoLocationResult | None]:
    """Geocode multiple addresses in batch."""
    if not addresses:
        return []

    # Normalize all addresses
    normalized = [
        NormalizedAddress(
            order=i,
            address=addr,
            city_info=_get_city_info(addr.city, addr.state),
            street_norm=normalize_text(addr.street) if addr.street else "",
            neighborhood_norm=(
                normalize_text(addr.neighborhood) if addr.neighborhood else ""
            ),
            zip_code=(
                "".join(c for c in str(addr.zip_code) if c.isdigit()).zfill(8)
                if addr.zip_code
                else None
            ),
            number=addr.street_number,
        )
        for i, addr in enumerate(addresses)
    ]

    # Filter valid and sort by city+street for batching
    valid = sorted(
        (n for n in normalized if n.street_norm and n.city_info),
        key=lambda n: (n.city_info.city_code, n.street_norm),
    )

    results: list[GeoLocationResult | None] = [None] * len(addresses)

    for i in range(0, len(valid), batch_size):
        batch = valid[i : i + batch_size]
        embeddings = _encode_streets_batch(
            [addr.street_norm for addr in batch], len(batch)
        )

        for addr, embedding in zip(batch, embeddings):
            cluster = None

            # Try CEP search first
            if addr.zip_code and not is_multi_street_cep(addr.zip_code):
                cluster = search_by_cep(
                    addr.zip_code, addr.street_norm, addr.neighborhood_norm
                )

            # Fall back to vector search
            if not cluster:
                query_ids = search_vector_index(embedding, addr.city_info.city_code, limit=20)
                if query_ids:
                    street_names = query_street_query(query_ids, addr.city_info.city_code)
                    if street_names:
                        clusters = _fetch_clusters_by_street_names(
                            street_names, addr.city_info.city_code
                        )
                        if clusters:
                            cluster = find_best_street_match(
                                clusters,
                                addr.street_norm,
                                addr.neighborhood_norm,
                                min_neighborhood_similarity=0,
                            )

            if cluster:
                results[addr.order] = _build_result(
                    cluster,
                    addr.address.street or "",
                    addr.street_norm,
                    addr.neighborhood_norm,
                    addr.zip_code,
                    addr.number,
                    addr.city_info,
                )

    return results