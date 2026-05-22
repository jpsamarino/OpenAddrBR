"""Tantivy text search index — instance-based with configurable data path."""

from pathlib import Path

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir


class TantivySearch:
    """Tantivy text search with lazy index loading per instance.

    Args:
        index_name: Name of the index directory (e.g. 'city_index', 'neighborhood_index').
        data_path: Path to data directory. Defaults to env var or package default.
    """

    _ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()

    def __init__(self, index_name: str, data_path: Path | None = None):
        """Initialize with index name and optional data path.

        Args:
            index_name: Name of the index directory (e.g. 'city_index', 'neighborhood_index').
            data_path: Path to data directory (parent of tantivy/ folder).
                      Defaults to env var or package default.
        """
        self._index_name = index_name
        self._data_path = data_path or get_tantivy_dir()
        self._index: tantivy.Index | None = None

    def _get_index(self) -> tantivy.Index:
        """Lazy index initialization — called once per instance."""
        if self._index is None:
            # _data_path is already the tantivy/ subdir path when using default,
            # but if user provides data_path we need to append tantivy/
            base_path = self._data_path
            # Detect if base_path already includes tantivy/ subfolder
            tantivy_subpath = base_path / "tantivy"
            if tantivy_subpath.exists():
                index_path = tantivy_subpath / self._index_name
            else:
                index_path = base_path / self._index_name
            self._index = tantivy.Index.open(str(index_path))
            self._index.register_tokenizer("ngram", self._ngram_analyzer)
        return self._index

    def schema(self):
        """Return the index schema."""
        return self._get_index().schema

    def searcher(self):
        """Return a searcher for this index."""
        return self._get_index().searcher()

    def _build_ngram_query(
        self,
        query_text: str,
        field_name: str,
        schema,
        min_match: int | None = None,
    ) -> tantivy.Query | None:
        """BooleanQuery with SHOULD (OR) per token."""
        tokens = self._ngram_analyzer.analyze(query_text)
        if not tokens:
            return None

        subqueries = [
            (Occur.Should, tantivy.Query.term_query(schema, field_name, t)) for t in tokens
        ]

        if min_match is None:
            n = len(tokens)
            if n <= 3:
                min_match = 1
            elif n <= 8:
                min_match = n // 2
            else:
                min_match = n // 3 * 2

        return tantivy.Query.boolean_query(subqueries, min_match)

    def search_cities(self, query_text: str, limit: int = 10) -> list[tuple[float, int]]:
        """Search cities by text only.

        Args:
            query_text: Normalized city name text.
            limit: Max results to return.

        Returns:
            List of (score, doc_address) tuples.
        """
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        ngram_query = self._build_ngram_query(query_text, "city_search", schema)
        if ngram_query is None:
            return []

        results = searcher.search(ngram_query, limit=limit)
        return list(results.hits)

    def search_neighborhoods(
        self, query_text: str, city_code: int, limit: int = 10
    ) -> list[tuple[float, int]]:
        """Search neighborhoods by text filtered by city_code.

        Args:
            query_text: Normalized neighborhood name text.
            city_code: IBGE city code to filter by.
            limit: Max results to return.

        Returns:
            List of (score, doc_address) tuples.
        """
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        ngram_query = self._build_ngram_query(
            query_text, "neighborhood_search", schema, min_match=1
        )
        if ngram_query is None:
            return []

        subqueries = [
            (Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code)),
            (Occur.Should, ngram_query),
        ]

        final_query = tantivy.Query.boolean_query(subqueries, 1)
        results = searcher.search(final_query, limit=limit)
        return list(results.hits)