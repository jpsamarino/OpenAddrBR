"""Usearch vector index — thread-safe with lazy initialization."""

import numpy as np
from cachetools import LRUCache
from usearch.index import Index as usearch_Index

from openaddrbr.core._env import get_usearch_dir


class UsearchIndex:
    """Thread-safe usearch index accessor with lazy initialization per city_code.

    Indexes are cached after first load per city_code with LRU eviction.
    Use clear_cache() for testing only.
    """

    _cache: LRUCache = LRUCache(maxsize=256)

    @classmethod
    def get(cls, city_code: int) -> "usearch_Index | None":
        """Get cached usearch index for city_code. Creates once per city_code."""
        if city_code not in cls._cache:
            if usearch_Index is None:
                cls._cache[city_code] = None
                return None
            index_path = get_usearch_dir() / f"{city_code}.usearch"
            if not index_path.exists():
                cls._cache[city_code] = None
                return None
            cls._cache[city_code] = usearch_Index(path=str(index_path), view=True)
        return cls._cache[city_code]

    @classmethod
    def search(cls, embedding, city_code: int, limit: int = 20) -> list[int]:
        """Search for query_ids by vector similarity."""
        index = cls.get(city_code)
        if index is None:
            return []
        results = index.search(embedding.astype(np.float32), count=limit)
        return [int(r.key) for r in results]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear index cache — for testing only."""
        cls._cache.clear()