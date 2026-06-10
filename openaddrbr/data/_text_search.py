"""Text search engine using Tantivy — unified index for cities and neighborhoods."""

from pathlib import Path

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core.env import get_tantivy_dir
from openaddrbr.core.interfaces import TextIndexSearcher
from openaddrbr.core.models import CityInfo, NeighborhoodInfo, SearchHit
from openaddrbr.utils import normalize_text


class TextSearchEngine(TextIndexSearcher):
    """Unified Tantivy text search engine for cities and neighborhoods.

    Loads indices lazily on first use and caches searchers internally.
    Single instance manages all text search indices.

    Args:
        data_path: Path to data directory (parent of tantivy/ folder).
                   Defaults to env var or package default.
    """

    _ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()
    _ngram_prefix = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=True)).build()
    _ngram_34 = TextAnalyzerBuilder(Tokenizer.ngram(3, 4, prefix_only=False)).build()

    def __init__(self, data_path: Path | None = None):
        self._data_path = data_path or get_tantivy_dir()
        self._city_index: tantivy.Index | None = None
        self._neighborhood_index: tantivy.Index | None = None
        self._street_index: tantivy.Index | None = None
        self._city_searcher: tantivy.Searcher | None = None
        self._neighborhood_searcher: tantivy.Searcher | None = None
        self._street_searcher: tantivy.Searcher | None = None

    def _resolve_path(self, index_name: str) -> Path:
        """Resolve index path, checking for tantivy subfolder."""
        base_path = self._data_path
        tantivy_subpath = base_path / "tantivy"
        if tantivy_subpath.exists():
            return tantivy_subpath / index_name
        return base_path / index_name

    def _open_index(self, index_name: str) -> tantivy.Index:
        """Open and configure a tantivy index."""
        index_path = str(self._resolve_path(index_name))
        index = tantivy.Index.open(index_path)
        index.register_tokenizer("ngram", self._ngram_analyzer)
        return index

    def _get_city_index(self) -> tantivy.Index:
        """Lazy load city index."""
        if self._city_index is None:
            self._city_index = self._open_index("city_index")
        return self._city_index

    def _get_neighborhood_index(self) -> tantivy.Index:
        """Lazy load neighborhood index."""
        if self._neighborhood_index is None:
            self._neighborhood_index = self._open_index("neighborhood_index")
        return self._neighborhood_index

    def _get_street_index(self) -> tantivy.Index:
        """Lazy load street index."""
        if self._street_index is None:
            self._street_index = self._open_index("city_street_index")
        return self._street_index

    def _get_city_searcher(self) -> tantivy.Searcher:
        """Get cached city searcher, creating it lazily if needed."""
        if self._city_searcher is None:
            self._city_searcher = self._get_city_index().searcher()
        return self._city_searcher

    def _get_neighborhood_searcher(self) -> tantivy.Searcher:
        """Get cached neighborhood searcher, creating it lazily if needed."""
        if self._neighborhood_searcher is None:
            self._neighborhood_searcher = self._get_neighborhood_index().searcher()
        return self._neighborhood_searcher

    def _get_street_searcher(self) -> tantivy.Searcher:
        """Get cached street searcher, creating it lazily if needed."""
        if self._street_searcher is None:
            self._street_searcher = self._get_street_index().searcher()
        return self._street_searcher

    def _build_ngram_query(
        self,
        query_text: str,
        field_name: str,
        schema,
    ) -> tantivy.Query | None:
        """BooleanQuery with SHOULD (OR) per token."""
        tokens = self._ngram_analyzer.analyze(query_text)
        if not tokens:
            return None

        subqueries = [
            (Occur.Should, tantivy.Query.term_query(schema, field_name, t)) for t in tokens
        ]

        return tantivy.Query.boolean_query(subqueries, minimum_number_should_match=1)

    def _build_autocomplete_query(self, query_text: str, schema) -> tantivy.Query | None:
        """Autocomplete query with prefix boost for last term."""
        terms = [t for t in query_text.strip().split() if t]
        if not terms:
            return None

        subs = []

        if len(terms) == 1:
            tokens = self._ngram_prefix.analyze(query_text)
        else:
            for term in terms[:-1]:
                tokens = self._ngram_34.analyze(term)
                for t in tokens:
                    if t:
                        subs.append((Occur.Should, tantivy.Query.term_query(schema, "street_search", t)))

            tokens = self._ngram_prefix.analyze(terms[-1])

        for t in tokens:
            if t:
                subs.append((Occur.Should, tantivy.Query.term_query(schema, "street_search", t)))

        if terms:
            last = terms[-1]
            if len(last) >= 2:
                try:
                    prefix_q = tantivy.Query.parse_query(f"street_search:{last}*", ["street_search"])
                    subs.append((Occur.Should, prefix_q))
                except Exception:
                    pass

        return tantivy.Query.boolean_query(subs, 1) if subs else None

    def search_cities(self, query_text: str, limit: int = 10) -> list[SearchHit]:
        """Search cities by normalized text.

        Args:
            query_text: Normalized city name text.
            limit: Max results to return.

        Returns:
            List of SearchHit(score, doc_address).
        """
        index = self._get_city_index()
        searcher = self._get_city_searcher()
        schema = index.schema

        ngram_query = self._build_ngram_query(query_text, "city_search", schema)
        if ngram_query is None:
            return []

        results = searcher.search(ngram_query, limit=limit)
        return [SearchHit(*hit) for hit in results.hits]

    def search_neighborhoods(
        self, query_text: str, city_code: int, limit: int = 10
    ) -> list[SearchHit]:
        """Search neighborhoods by normalized text filtered by city code.

        Args:
            query_text: Normalized neighborhood name text.
            city_code: IBGE city code to filter by.
            limit: Max results to return.

        Returns:
            List of SearchHit(score, doc_address).
        """
        index = self._get_neighborhood_index()
        searcher = self._get_neighborhood_searcher()
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
        return [SearchHit(*hit) for hit in results.hits]

    def search_streets(
        self, query_text: str, city_code: int, limit: int = 10, autocomplete_query: bool = False
    ) -> list[SearchHit]:
        index = self._get_street_index()
        searcher = self._get_street_searcher()
        schema = index.schema

        if autocomplete_query:
            ngram_query = self._build_autocomplete_query(query_text, schema)
        else:
            ngram_query = self._build_ngram_query(query_text, "street_search", schema)
        if ngram_query is None:
            return []

        subqueries = [
            (Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code)),
            (Occur.Should, ngram_query),
        ]

        final_query = tantivy.Query.boolean_query(subqueries, 1)
        results = searcher.search(final_query, limit=limit)
        return [SearchHit(*hit) for hit in results.hits]

    def get_query_ids_batch(self, doc_addresses: list[int]) -> list[int | None]:
        """Get query_ids for multiple street documents using a single searcher.

        Args:
            doc_addresses: List of Tantivy doc addresses from search_streets results.

        Returns:
            List of query_ids (int) or None for each doc_address.
        """
        if not doc_addresses:
            return []

        searcher = self._get_street_searcher()
        results: list[int | None] = []
        for addr in doc_addresses:
            try:
                doc = searcher.doc(addr)
                results.append(doc.get_first("query_id"))
            except KeyError:
                results.append(None)

        return results

    def get_cities_batch(self, doc_addresses: list[int]) -> list[CityInfo | None]:
        """Get cities for multiple doc addresses using a single searcher.

        Args:
            doc_addresses: List of Tantivy doc addresses from search_cities results.

        Returns:
            List of CityInfo or None for each doc_address.
        """
        if not doc_addresses:
            return []

        searcher = self._get_city_searcher()
        results: list[CityInfo | None] = []
        for addr in doc_addresses:
            try:
                doc = searcher.doc(addr)
                city_name = doc.get_first("city_name") or ""
                results.append(
                    CityInfo(
                        city_code=doc.get_first("city_code"),
                        city_name=city_name,
                        city_normalized=normalize_text(city_name),
                        state_code=doc.get_first("state_code"),
                        latitude=doc.get_first("ref_latitude"),
                        longitude=doc.get_first("ref_longitude"),
                    )
                )
            except KeyError:
                results.append(None)

        return results

    def get_neighborhoods_batch(self, doc_addresses: list[int]) -> list[NeighborhoodInfo | None]:
        """Get neighborhoods for multiple doc addresses using a single searcher.

        Args:
            doc_addresses: List of Tantivy doc addresses from search_neighborhoods results.

        Returns:
            List of NeighborhoodInfo or None for each doc_address.
        """
        if not doc_addresses:
            return []

        searcher = self._get_neighborhood_searcher()
        results: list[NeighborhoodInfo | None] = []
        for addr in doc_addresses:
            try:
                doc = searcher.doc(addr)
                neighborhood_name = doc.get_first("neighborhood_name") or ""
                results.append(
                    NeighborhoodInfo(
                        neighborhood_name=neighborhood_name,
                        neighborhood_normalized=normalize_text(neighborhood_name),
                        city_code=doc.get_first("city_code"),
                        latitude=doc.get_first("ref_latitude"),
                        longitude=doc.get_first("ref_longitude"),
                    )
                )
            except KeyError:
                results.append(None)

        return results
