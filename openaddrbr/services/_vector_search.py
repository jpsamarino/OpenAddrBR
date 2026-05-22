"""Vector search - embedding search and cluster fetching."""

import numpy as np

from openaddrbr.core.interfaces import GeocoderDB
from openaddrbr.core.models import StreetCluster
from openaddrbr.data._vector_search import VectorSearchEngine
from openaddrbr.utils import find_best_street_match


def search_by_embedding(
    city_code: int,
    embedding: np.ndarray,
    street_norm: str,
    neighborhood_norm: str,
    db: GeocoderDB,
    usearch_index: VectorSearchEngine | None = None,
) -> StreetCluster | None:
    """Search by complete address using vector search + exact SQL.

    Args:
        city_code: IBGE city code.
        embedding: Query embedding vector.
        street_norm: Normalized street name.
        neighborhood_norm: Normalized neighborhood name.
        db: Database interface.
        usearch_index: VectorSearchEngine instance. Required.

    Returns:
        Best matching StreetCluster or None.
    """
    if embedding is None or street_norm is None:
        return None

    if usearch_index is None:
        raise ValueError("usearch_index is required")

    query_ids = usearch_index.search_city_streets(
        city_code=city_code, embedding=embedding, limit=20
    )
    if not query_ids:
        return None

    street_names = db.query_street_query(query_ids)
    if not street_names:
        return None

    rows = db.query_address_by_street_names(street_names, city_code)
    if not rows:
        return None

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

    return find_best_street_match(
        clusters, street_norm, neighborhood_norm, min_neighborhood_similarity=0
    )