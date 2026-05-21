"""Neighborhood autocomplete search using Tantivy ngram index."""

import unicodedata

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir
from openaddrbr.core.models import NeighborhoodInfo

_ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()
_index = None

def _get_index():
    global _index
    if _index is None:
        index_path = str(get_tantivy_dir() / "neighborhood_index")
        _index = tantivy.Index.open(index_path)
        _index.register_tokenizer("ngram", _ngram_analyzer)
    return _index

def text_to_ascii(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text.upper())
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    return " ".join(text.split()).strip()

def build_neighborhood_query(query_text: str, city_code: int, schema) -> tantivy.Query | None:
    tokens = _ngram_analyzer.analyze(query_text)
    if not tokens:
        return None

    subqueries = [(Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code))]
    for token in tokens:
        subqueries.append((Occur.Should, tantivy.Query.term_query(schema, "neighborhood_search", token)))

    return tantivy.Query.boolean_query(subqueries, 1)

def search_neighborhood_tantivy(query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
    query_normalized = text_to_ascii(query)
    if not query_normalized:
        return []

    index = _get_index()
    searcher = index.searcher()
    schema = index.schema

    tantivy_query = build_neighborhood_query(query_normalized, city_code, schema)
    if tantivy_query is None:
        return []

    results = searcher.search(tantivy_query, limit=limit)

    neighborhoods = []
    for score, doc_address in results.hits:
        doc = searcher.doc(doc_address)
        neighborhood_name = doc.get_first("neighborhood_name") or ""
        neighborhoods.append(NeighborhoodInfo(
            neighborhood_name=neighborhood_name,
            neighborhood_normalized=text_to_ascii(neighborhood_name),
            city_code=doc.get_first("city_code"),
            latitude=doc.get_first("ref_latitude"),
            longitude=doc.get_first("ref_longitude"),
        ))

    return neighborhoods