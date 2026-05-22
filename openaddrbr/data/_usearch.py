"""Usearch vector index — instance-based with configurable data path."""

from pathlib import Path

import numpy as np
from cachetools import LRUCache
from usearch.index import Index as usearch_Index

from openaddrbr.core._env import get_usearch_dir


class UsearchIndex:
    """Usearch index accessor with per-instance cache and configurable data path.

    Args:
        data_path: Path to usearch directory. Defaults to env var or package default.
        maxsize: Max number of indices to keep in memory (LRU eviction).

    Example:
        index = UsearchIndex()
        results = index.search(embedding, city_code=1100015)

        # Or with custom path
        index = UsearchIndex(data_path="/custom/path")
        results = index.search(embedding, city_code=1100015)
    """

    def __init__(self, data_path: Path | None = None, maxsize: int = 256):
        self._data_path = data_path or get_usearch_dir()
        self._cache: LRUCache = LRUCache(maxsize=maxsize)

    def get(self, city_code: int) -> "usearch_Index | None":
        """Get cached usearch index for city_code. Creates once per city_code."""
        if city_code in self._cache:
            return self._cache[city_code]

        if usearch_Index is None:
            self._cache[city_code] = None
            return None

        index_path = self._data_path / f"{city_code}.usearch"
        if not index_path.exists():
            self._cache[city_code] = None
            return None

        index = usearch_Index(path=str(index_path), view=True)
        self._cache[city_code] = index
        return index

    def search(self, embedding, city_code: int, limit: int = 20) -> list[int]:
        """Search for query_ids by vector similarity."""
        index = self.get(city_code)
        if index is None:
            return []

        results = index.search(embedding.astype(np.float32), count=limit)
        return [int(r.key) for r in results]

    def clear_cache(self) -> None:
        """Clear the index cache."""
        self._cache.clear()