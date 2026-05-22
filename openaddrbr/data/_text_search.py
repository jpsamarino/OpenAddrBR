"""Text search engine using Tantivy — unified index for cities and neighborhoods."""

from pathlib import Path

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir


class TextSearchEngine:
    """Unified Tantivy text search engine for cities and neighborhoods.

    Loads indices lazily on first use and caches them internally.
    Single instance manages all text search indices.

    Args:
        data_path: Path to data directory (parent of tantivy/ folder).
                   Defaults to env var or package default.
    """

    _ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()

    def __init__(self, data_path: Path | None = None):
        self._data_path = data_path or get_tantivy_dir()
        self._indices: dict[str, tantivy.Index] = {}

    def _get_index(self, index_name: str) -> tantivy.Index:
        """Lazy load index by name."""
        if index_name not in self._indices:
            base_path = self._data_path
            tantivy_subpath = base_path / "tantivy"
            if tantivy_subpath.exists():
                index_path = tantivy_subpath / index_name
            else:
                index_path = base_path / index_name

            index = tantivy.Index.open(str(index_path))
            index.register_tokenizer("ngram", self._ngram_analyzer)
            self._indices[index_name] = index
        return self._indices[index_name]

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
        """Search cities by normalized text.

        Args:
            query_text: Normalized city name text.
            limit: Max results to return.

        Returns:
            List of (score, doc_address) tuples.
        """
        index = self._get_index("city_index")
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
        """Search neighborhoods by normalized text filtered by city code.

        Args:
            query_text: Normalized neighborhood name text.
            city_code: IBGE city code to filter by.
            limit: Max results to return.

        Returns:
            List of (score, doc_address) tuples.
        """
        index = self._get_index("neighborhood_index")
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