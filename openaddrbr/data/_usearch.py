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
        cache_size: Max number of indices to keep in memory (LRU eviction).

    Example:
        index = UsearchIndex()
        results = index.search_city_streets(city_code=1100015, embedding=embedding)

        # Or with custom path
        index = UsearchIndex(data_path="/custom/path")
        results = index.search_city_streets(city_code=1100015, embedding=embedding)
    """

    def __init__(self, data_path: Path | None = None, cache_size: int = 256):
        self._data_path = data_path or get_usearch_dir()
        self._cache: LRUCache = LRUCache(maxsize=cache_size)

    def get_city_street_index(self, city_code: int) -> "usearch_Index | None":
        """Load and cache the street index for a city.

        Args:
            city_code: IBGE city code.

        Returns:
            The usearch Index for this city, or None if not found.
        """
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

    def search_city_streets(
        self, city_code: int, embedding, limit: int = 20
    ) -> list[int]:
        """Search for street query_ids by vector similarity within a city.

        Args:
            city_code: IBGE city code to search within.
            embedding: Query embedding vector.
            limit: Max number of results.

        Returns:
            List of street query_ids matching the embedding.
        """
        index = self.get_city_street_index(city_code)
        if index is None:
            return []

        results = index.search(embedding.astype(np.float32), count=limit)
        return [int(r.key) for r in results]

    def clear(self) -> None:
        """Clear the index cache."""
        self._cache.clear()