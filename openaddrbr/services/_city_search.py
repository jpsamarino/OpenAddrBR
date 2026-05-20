"""City autocomplete search using Tantivy ngram index."""

import unicodedata

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir
from openaddrbr.core.models import CityInfo

# Global ngram analyzer - same as benchmark
_ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()

# Module-level cached index
_index = None


def _get_index():
    """Get or open the Tantivy city index."""
    global _index
    if _index is None:
        index_path = str(get_tantivy_dir() / "city_index")
        _index = tantivy.Index.open(index_path)
        _index.register_tokenizer("ngram", _ngram_analyzer)
    return _index


def text_to_ascii(text: str) -> str:
    """Normalize text for ASCII, uppercase."""
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text.upper())
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    text = " ".join(text.split())
    return text.strip()


def build_ngram_query(query_text: str, field_name: str, schema) -> tantivy.Query | None:
    """BooleanQuery with SHOULD (OR) per token — same logic as benchmark."""
    tokens = _ngram_analyzer.analyze(query_text)
    if not tokens:
        return None

    subqueries = [(Occur.Should, tantivy.Query.term_query(schema, field_name, t)) for t in tokens]

    n = len(tokens)
    if n <= 3:
        min_match = 1
    elif n <= 8:
        min_match = n // 2
    else:
        min_match = n // 3 * 2

    return tantivy.Query.boolean_query(subqueries, min_match)


def search_city_tantivy(query: str, limit: int = 10) -> list[CityInfo]:
    """Search for cities using ngram autocomplete.

    Args:
        query: City name query (partial match supported)
        limit: Maximum number of results

    Returns:
        List of CityInfo objects with coordinates
    """
    query_normalized = text_to_ascii(query)
    if not query_normalized:
        return []

    index = _get_index()
    searcher = index.searcher()
    schema = index.schema

    tantivy_query = build_ngram_query(query_normalized, "city_search", schema)
    if tantivy_query is None:
        return []

    results = searcher.search(tantivy_query, limit=limit)

    cities = []
    for score, doc_address in results.hits:
        doc = searcher.doc(doc_address)
        city_name = doc.get_first("city_name") or ""
        cities.append(
            CityInfo(
                city_code=doc.get_first("city_code"),
                city_name=city_name,
                city_normalized=text_to_ascii(city_name),
                state_code=doc.get_first("state_code"),
                latitude=doc.get_first("ref_latitude"),
                longitude=doc.get_first("ref_longitude"),
            )
        )

    return cities