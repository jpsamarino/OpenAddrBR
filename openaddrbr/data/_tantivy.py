"""Tantivy text search index base class."""

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir


class TantivySearch:
    """Base class for tantivy text search with lazy index loading."""

    _ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()

    def __init__(self, index_name: str):
        """Initialize with the index directory name (e.g. 'city_index', 'neighborhood_index')."""
        self._index_name = index_name
        self._index: tantivy.Index | None = None

    def _get_index(self) -> tantivy.Index:
        """Lazy index initialization — called once per instance."""
        if self._index is None:
            index_path = str(get_tantivy_dir() / self._index_name)
            self._index = tantivy.Index.open(index_path)
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

    def search_text(self, query_text: str, limit: int = 10) -> list[tuple[float, int]]:
        """Search cities by text only."""
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        ngram_query = self._build_ngram_query(query_text, "city_search", schema)
        if ngram_query is None:
            return []

        final_query = tantivy.Query.boolean_query([(Occur.Must, ngram_query)], 1)
        results = searcher.search(final_query, limit=limit)
        return list(results.hits)

    def search_neighborhoods(
        self, query_text: str, city_code: int, limit: int = 10
    ) -> list[tuple[float, int]]:
        """Search neighborhoods by text filtered by city_code."""
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        ngram_query = self._build_ngram_query(query_text, "neighborhood_search", schema)
        if ngram_query is None:
            return []

        subqueries = [
            (Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code)),
            (Occur.Should, ngram_query),
        ]

        final_query = tantivy.Query.boolean_query(subqueries, 1)
        results = searcher.search(final_query, limit=limit)
        return list(results.hits)