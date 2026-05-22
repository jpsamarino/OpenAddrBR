"""Vector search engine using usearch — instance-based with configurable data path."""

from pathlib import Path

import numpy as np
from cachetools import LRUCache
from usearch.index import Index as usearch_Index

from openaddrbr.core.env import get_usearch_dir


class VectorSearchEngine:
    """Vector search engine using usearch with per-instance cache.

    Args:
        data_path: Path to usearch directory. Defaults to env var or package default.
        cache_size: Max number of indices to keep in memory (LRU eviction).

    Example:
        engine = VectorSearchEngine()
        results = engine.search_city_streets(city_code=1100015, embedding=embedding)

        # Or with custom path
        engine = VectorSearchEngine(data_path="/custom/path")
        results = engine.search_city_streets(city_code=1100015, embedding=embedding)
    """

    def __init__(self, data_path: Path | None = None, cache_size: int = 256):
        if data_path is None:
            # Default: use env function which already returns usearch_v2 path
            self._data_path = get_usearch_dir()
        elif (data_path / "usearch_v2").exists():
            # If given dbs/ path, use the usearch_v2 subfolder
            self._data_path = data_path / "usearch_v2"
        else:
            # Otherwise assume it's already the usearch_v2 folder or similar
            self._data_path = data_path
        self._cache: LRUCache = LRUCache(maxsize=cache_size)

    def get_city_street_index(self, city_code: int):
        """Load and cache the street index for a city.

        Args:
            city_code: IBGE city code.

        Returns:
            The usearch Index for this city.
        """
        if city_code in self._cache:
            return self._cache[city_code]

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