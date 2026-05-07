"""Usearch index loading and management."""

import os
from functools import lru_cache
from typing import Optional
import numpy as np

try:
    from usearch.index import Index as usearch_Index
except ImportError:
    usearch_Index = None

from openaddrbr.data._config import get_usearch_dir


@lru_cache(maxsize=128)
def get_semantic_index(city_code: int) -> Optional["usearch_Index"]:
    """Load usearch city index with LRU cache."""
    if usearch_Index is None:
        return None

    index_path = get_usearch_dir() / f"{city_code}.usearch"
    if not index_path.exists():
        return None
    return usearch_Index(path=str(index_path), view=True)


def search_vector(
    embedding, city_code: int, limit: int = 20
) -> list[int]:
    """Search for query_ids by vector similarity using usearch."""
    index = get_semantic_index(city_code)
    if index is None:
        return []

    results = index.search(embedding.astype(np.float32), count=limit)
    return [int(r.key) for r in results]