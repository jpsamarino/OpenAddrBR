"""
Benchmark runner comparing two implementations:
1. SQLite3 (_db_ref_base.py)
2. APSW module-level singleton (_db.py)
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass

# SQLite3
from benchmarks._db_ref_base import (
    get_connection,
    close_connection,
    get_city_info_from_db,
    is_multi_street_cep,
    query_address_by_cep,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
    query_address_by_street_names,
    query_query_ids,
)

# APSW module-level
from openaddrbr.data import (
    close_connection as apsw_close_connection,
    get_city_info_from_db as apsw_get_city_info,
    is_multi_street_cep as apsw_is_multi_street_cep,
    query_address_by_cep as apsw_query_address_by_cep,
    query_full_address_by_street_id as apsw_query_full_address_by_street_id,
    query_geo_locations as apsw_query_geo_locations,
    query_street_query as apsw_query_street_query,
    query_address_by_street_names as apsw_query_address_by_street_names,
    query_query_ids as apsw_query_query_ids,
)


@dataclass
class BenchmarkResult:
    name: str
    total_ms: float
    count: int
    ns_per_query: float
    queries_per_sec: float


def load_json(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def benchmark_fn_sync(name: str, fn, data: list, warmup_runs: int = 3) -> BenchmarkResult:
    count = len(data)

    # Warmup
    for _ in range(warmup_runs):
        for item in data[:min(100, count)]:
            fn(item)

    # Benchmark
    t0 = time.perf_counter()
    for item in data:
        fn(item)
    elapsed_ns = (time.perf_counter() - t0) * 1_000_000_000

    ns_per_query = elapsed_ns / count if count > 0 else 0
    qps = 1_000_000_000 / ns_per_query if ns_per_query > 0 else 0

    return BenchmarkResult(
        name=name,
        total_ms=elapsed_ns / 1_000_000,
        count=count,
        ns_per_query=ns_per_query,
        queries_per_sec=qps,
    )


def print_result(r: BenchmarkResult):
    print(f"  {r.name:<40} | {r.ns_per_query:>10.0f} ns/q | {r.queries_per_sec:>8.0f} qps | {r.count:>6,}x")


def run_benchmarks(name: str, impl: dict, data_dir: Path):
    datasets = {
        "get_city_info": load_json(data_dir / "get_city_info.json"),
        "is_multi_street_cep": load_json(data_dir / "is_multi_street_cep.json"),
        "fetch_address_by_cep": load_json(data_dir / "fetch_address_by_cep.json"),
        "fetch_address_by_street_id": load_json(data_dir / "fetch_address_by_street_id.json"),
        "fetch_geo_location": load_json(data_dir / "fetch_geo_location.json"),
        "fetch_street_by_query_ids": load_json(data_dir / "fetch_street_by_query_ids.json"),
        "fetch_address_by_street_names": load_json(data_dir / "fetch_address_by_street_names.json"),
        "fetch_query_ids": load_json(data_dir / "fetch_query_ids.json"),
    }

    for db_name, data in datasets.items():
        print(f"  {db_name}: {len(data):,} items")

    impl["init"]()

    print()
    print("=" * 85)
    print(f"BENCHMARK: {name}")
    print("=" * 85)
    print(f"{'Function':<42} | {'ns/query':>12} | {'qps':>10} | {'count':>8}")
    print("-" * 85)

    results = []

    r = benchmark_fn_sync("get_city_info", lambda p: impl["get_city_info"](p[0], p[1]), datasets["get_city_info"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("is_multi_street_cep", lambda p: impl["is_multi_street_cep"](p), datasets["is_multi_street_cep"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_address_by_cep", lambda p: impl["query_address_by_cep"](str(p), limit=10), datasets["fetch_address_by_cep"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_address_by_street_id", lambda p: impl["query_full_address_by_street_id"](p), datasets["fetch_address_by_street_id"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_geo_location", lambda p: impl["query_geo_locations"](p["street_id"], p["number"], limit=3), datasets["fetch_geo_location"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_street_by_query_ids", lambda p: impl["query_street_query"](p[0], p[1]), datasets["fetch_street_by_query_ids"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_address_by_street_names", lambda p: impl["query_address_by_street_names"](p[0], p[1]), datasets["fetch_address_by_street_names"])
    results.append(r)
    print_result(r)

    r = benchmark_fn_sync("fetch_query_ids", lambda p: impl["query_query_ids"](p), datasets["fetch_query_ids"])
    results.append(r)
    print_result(r)

    impl["close"]()

    return {r.name: r for r in results}


def main():
    data_dir = Path(__file__).parent / "data_benchmarks_db"

    print("=" * 85)
    print("DB BENCHMARK - 2 implementations comparison")
    print("=" * 85)

    # _db_ref_base.py (SQLite3)
    sqlite_impl = {
        "init": get_connection,
        "close": close_connection,
        "get_city_info": get_city_info_from_db,
        "is_multi_street_cep": is_multi_street_cep,
        "query_address_by_cep": query_address_by_cep,
        "query_full_address_by_street_id": query_full_address_by_street_id,
        "query_geo_locations": query_geo_locations,
        "query_street_query": query_street_query,
        "query_address_by_street_names": query_address_by_street_names,
        "query_query_ids": query_query_ids,
    }

    # _db.py (APSW module-level singleton)
    apsw_impl = {
        "init": lambda: None,
        "close": apsw_close_connection,
        "get_city_info": apsw_get_city_info,
        "is_multi_street_cep": apsw_is_multi_street_cep,
        "query_address_by_cep": apsw_query_address_by_cep,
        "query_full_address_by_street_id": apsw_query_full_address_by_street_id,
        "query_geo_locations": apsw_query_geo_locations,
        "query_street_query": apsw_query_street_query,
        "query_address_by_street_names": apsw_query_address_by_street_names,
        "query_query_ids": apsw_query_query_ids,
    }

    print("\n[1/2] _db_ref_base.py (SQLite3)...")
    results_sqlite = run_benchmarks("_db_ref_base.py (SQLite3)", sqlite_impl, data_dir)

    print("\n[2/2] _db.py (APSW singleton)...")
    results_apsw = run_benchmarks("_db.py (APSW singleton)", apsw_impl, data_dir)

    # Comparison
    print()
    print("=" * 100)
    print("COMPARISON (ns/query)")
    print("=" * 100)
    print(f"{'Function':<42} | {'_db_ref_base':>14} | {'_db.py':>14} | {'Best':>12}")
    print("-" * 100)

    for name in results_sqlite:
        r_sql = results_sqlite[name]
        r_apsw = results_apsw[name]

        times = {"_db_ref_base": r_sql.ns_per_query, "_db": r_apsw.ns_per_query}
        best = min(times, key=times.get)
        speedup = max(times.values()) / min(times.values())

        print(f"  {r_sql.name:<40} | {r_sql.ns_per_query:>12.0f}ns | {r_apsw.ns_per_query:>12.0f}ns | {best} ({speedup:.1f}x)")

    print()
    print("=" * 85)
    print("[DONE]")


if __name__ == "__main__":
    main()