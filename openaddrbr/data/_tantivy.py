"""Tantivy text search index base class."""

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir


class TantivySearch:
    """Base class for tantivy text search with lazy index loading.

    Subclasses should call _get_index() and use search_raw() for basic queries,
    or extend _build_ngram_query() for custom query building.
    """

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

    def _build_ngram_query(
        self,
        query_text: str,
        field_name: str,
        schema,
        min_match: int | None = None,
    ) -> tantivy.Query | None:
        """BooleanQuery with SHOULD (OR) per token.

        Args:
            query_text: Raw query text (should already be normalized)
            field_name: Field name in tantivy schema to search
            schema: Index schema
            min_match: Minimum number of tokens that must match. If None, auto-calculated.

        Returns:
            Tantivy Query or None if query_text produces no tokens.
        """
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

    def search_raw(
        self,
        query_text: str,
        field_name: str,
        city_code: int | None = None,
        limit: int = 10,
    ) -> list[tuple[float, int]]:
        """Raw search returning (score, doc_address) tuples.

        Args:
            query_text: Normalized query text
            field_name: Field name in tantivy schema
            city_code: Optional city_code filter (adds Must clause)
            limit: Max results

        Returns:
            List of (score, doc_address) tuples
        """
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        subqueries: list[tuple[Occur, tantivy.Query]] = []

        if city_code is not None:
            subqueries.append(
                (Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code))
            )

        ngram_query = self._build_ngram_query(query_text, field_name, schema)
        if ngram_query is None:
            return []

        subqueries.append((Occur.Should, ngram_query))

        # When no city_code filter: use Must(ngram_query) to require at least one match
        # When city_code is set: use all subqueries (Must city_code + Should ngram_query)
        final_query = tantivy.Query.boolean_query(
            subqueries, 1,
        )
        results = searcher.search(final_query, limit=limit)
        return [(float(score), doc_address) for score, doc_address in results.hits]