"""Benchmark script for search_streets performance."""

import sqlite3
import time

from openaddrbr.core._location_search import LocationSearch
from openaddrbr.utils import normalize_text

TOTAL = 10000
AUTOCOMPLETE_QUERY = True  # Toggle to switch between autocomplete and ngram search

SGEODB = "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db"


def load_random_queries(total: int) -> list[tuple[str, int]]:
    """Load random street queries from database."""
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        f"""
        SELECT street_normalized, CAST(city_code AS INTEGER) as city_code
        FROM street_query
        WHERE street_normalized NOT IN ('0','00','000','0000','00000','000000','0000000')
          AND street_normalized GLOB '*[a-zA-Z]*'
          AND LENGTH(street_normalized) > 2
          AND city_code IS NOT NULL
        ORDER BY RANDOM()
        LIMIT {total}
        """
    ).fetchall()
    conn.close()
    return [(r[0], r[1]) for r in rows]


def benchmark_full_flow(queries: list[tuple[str, int]]) -> float:
    """Benchmark full search_streets flow."""
    search = LocationSearch()

    # Warmup
    for q, city_code in queries[:100]:
        search.search_streets(city_code=city_code, query=q, limit=10, autocomplete_query=AUTOCOMPLETE_QUERY)

    # Benchmark
    start = time.perf_counter()
    for q, city_code in queries:
        search.search_streets(city_code=city_code, query=q, limit=10, autocomplete_query=AUTOCOMPLETE_QUERY)
    elapsed = time.perf_counter() - start

    qps = len(queries) / elapsed
    print(f"Full flow: {len(queries)} queries in {elapsed:.2f}s = {qps:.0f} QPS")
    return qps


def benchmark_tantivy_only(queries: list[tuple[str, int]]) -> float:
    """Benchmark Tantivy search only."""
    search = LocationSearch()
    engine = search._engine

    # Benchmark
    all_hits = []
    start = time.perf_counter()
    for q, city_code in queries:
        hits = engine.search_streets(
            normalize_text(q), city_code, limit=10, autocomplete_query=AUTOCOMPLETE_QUERY
        )
        all_hits.append(hits)
    elapsed = time.perf_counter() - start

    qps = len(queries) / elapsed
    print(f"Tantivy only: {len(queries)} queries in {elapsed:.2f}s = {qps:.0f} QPS")

    return qps, all_hits


def benchmark_tantivy_and_postprocess(queries: list[tuple[str, int]]) -> float:
    """Benchmark get_query_ids_batch + SQL + postprocessing."""
    print("Benchmarking Tantivy + get_query_ids + SQL...")
    search = LocationSearch()
    engine = search._engine
    addr_store = search._addr_store

    start = time.perf_counter()
    _, sample_hits = benchmark_tantivy_only(queries)

    for hits in sample_hits:
        doc_addresses = [hit.doc_address for hit in hits]
        query_ids_list = engine.get_query_ids_batch(doc_addresses)
        query_ids = [qid for qid in query_ids_list if qid is not None]
        if query_ids:
            segments = addr_store.query_streets_by_query_id(query_ids)
    elapsed = time.perf_counter() - start

    qps = len(sample_hits) / elapsed
    print(
        f"Tantivy + get_query_ids + SQL ({len(sample_hits)} sample): {len(sample_hits)} queries in {elapsed:.2f}s = {qps:.0f} QPS"
    )
    return qps


def main():
    mode = "autocomplete" if AUTOCOMPLETE_QUERY else "ngram"
    print(f"Tantivy street search benchmark - {TOTAL} random queries ({mode} mode)\n")
    print(f"Loading {TOTAL} random queries from {SGEODB}...")
    queries = load_random_queries(TOTAL)
    print(f"Loaded {len(queries)} queries\n")

    # Warm up
    print("=== Warming up ===")
    search = LocationSearch()
    for q, city_code in queries[:100]:
        search.search_streets(city_code=city_code, query=q, limit=10, autocomplete_query=AUTOCOMPLETE_QUERY)
    print()

    # Benchmarks
    print("=== Benchmarks ===")
    qps_tantivy, all_hits = benchmark_tantivy_only(queries)
    qps_sql = benchmark_tantivy_and_postprocess(queries)
    qps_full = benchmark_full_flow(queries)

    print()
    print("=== Summary ===")
    print(f"Tantivy only:        {qps_tantivy:.0f} QPS")
    print(f"get_query_id + SQL:  ~{qps_sql:.0f} QPS")
    print(f"Full flow:           {qps_full:.0f} QPS")


if __name__ == "__main__":
    main()