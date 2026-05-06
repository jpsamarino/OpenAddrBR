"""CEP search service - search_by_cep implementation."""

from functools import lru_cache

from openaddrbr.core.models import StreetCluster
from openaddrbr.data import query_address_by_cep, is_multi_street_cep as _is_multi_street_cep
from openaddrbr.utils import find_best_street_match


@lru_cache(maxsize=10000)
def is_multi_street_cep(cep: str) -> bool:
    """Check if CEP has multiple streets."""
    return _is_multi_street_cep(cep)


def search_by_cep(
    zip_code: str,
    street_norm: str,
    neighborhood_norm: str,
    limit_qt_street: int = 10,
) -> StreetCluster | None:
    """Search for street_id by CEP."""
    rows = query_address_by_cep(zip_code, limit_qt_street)

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
        clusters,
        street_norm,
        neighborhood_norm,
    )