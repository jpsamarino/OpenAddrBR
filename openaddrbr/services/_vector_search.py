"""Vector search - embedding search and cluster fetching."""

import numpy as np

from openaddrbr.core.models import StreetCluster
from openaddrbr.data import (
    query_address_by_street_names,
    query_street_query,
    search_vector as search_vector_index,
)
from openaddrbr.utils import find_best_street_match


def _fetch_clusters_by_street_names(street_names: list[str], city_code: int) -> list[StreetCluster]:
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

    street_names = query_street_query(query_ids, city_code)
    if not street_names:
        return None

    clusters = _fetch_clusters_by_street_names(street_names, city_code)
    if not clusters:
        return None
    return find_best_street_match(
        clusters, street_norm, neighborhood_norm, min_neighborhood_similarity=0
    )
