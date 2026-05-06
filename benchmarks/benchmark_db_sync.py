"""
Benchmark runner for SYNC ISGEODatabase implementations.
Measures query throughput in ns per operation.
"""

import json
import time
from pathlib import Path
from dataclasses import dataclass

from domain.repositories.ISGEODatabase import ISGEODatabase


@dataclass
class BenchmarkResult:
    """Resultado de benchmark de uma função."""
    name: str
    total_ms: float
    count: int
    ns_per_query: float
    queries_per_sec: float


def load_json(path: Path) -> list:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def benchmark_fn_sync(
    name: str,
    fn,
    data: list,
    warmup_runs: int = 3
) -> BenchmarkResult:
    """Roda benchmark de uma função sync com os dados fornecidos."""
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


def run_benchmarks_sync(db: ISGEODatabase, data_dir: Path):
    """Roda todos os benchmarks para uma implementação sync de banco."""
    print(f"\nLoading datasets from {data_dir}...")

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

    for name, data in datasets.items():
        print(f"  {name}: {len(data):,} items")

    # Sync version doesn't need initialize() but we call it for interface consistency
    try:
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.initialize())
    except:
        pass

    print()
    print("=" * 85)
    print(f"BENCHMARK: {db.__class__.__name__} (SYNC)")
    print("=" * 85)
    print(f"{'Function':<42} | {'ns/query':>12} | {'qps':>10} | {'count':>8}")
    print("-" * 85)

    results = []

    # get_city_info(city_name, state_code)
    r = benchmark_fn_sync(
        "get_city_info",
        lambda p: db.get_city_info(p[0], p[1]),
        datasets["get_city_info"],
    )
    results.append(r)
    print_result(r)

    # is_multi_street_cep(cep)
    r = benchmark_fn_sync(
        "is_multi_street_cep",
        lambda p: db.is_multi_street_cep(p),
        datasets["is_multi_street_cep"],
    )
    results.append(r)
    print_result(r)

    # fetch_address_by_cep(zip_code)
    r = benchmark_fn_sync(
        "fetch_address_by_cep",
        lambda p: db.fetch_address_by_cep(p),
        datasets["fetch_address_by_cep"],
    )
    results.append(r)
    print_result(r)

    # fetch_address_by_street_id(street_id)
    r = benchmark_fn_sync(
        "fetch_address_by_street_id",
        lambda p: db.fetch_address_by_street_id(p),
        datasets["fetch_address_by_street_id"],
    )
    results.append(r)
    print_result(r)

    # fetch_geo_location(street_id, number)
    r = benchmark_fn_sync(
        "fetch_geo_location",
        lambda p: db.fetch_geo_location(p["street_id"], p["number"]),
        datasets["fetch_geo_location"],
    )
    results.append(r)
    print_result(r)

    # fetch_street_by_query_ids(query_ids, city_code)
    r = benchmark_fn_sync(
        "fetch_street_by_query_ids",
        lambda p: db.fetch_street_by_query_ids(p[0], p[1]),
        datasets["fetch_street_by_query_ids"],
    )
    results.append(r)
    print_result(r)

    # fetch_address_by_street_names(street_names, city_code)
    r = benchmark_fn_sync(
        "fetch_address_by_street_names",
        lambda p: db.fetch_address_by_street_names(p[0], p[1]),
        datasets["fetch_address_by_street_names"],
    )
    results.append(r)
    print_result(r)

    # fetch_query_ids(city_code)
    r = benchmark_fn_sync(
        "fetch_query_ids",
        lambda p: db.fetch_query_ids(p),
        datasets["fetch_query_ids"],
    )
    results.append(r)
    print_result(r)

    try:
        import asyncio
        asyncio.get_event_loop().run_until_complete(db.close())
    except:
        pass

    return results


def main():
    from application._db_sync import SGEODatabaseSync

    data_dir = Path(__file__).parent / "data_benchmarks_db"

    print("=" * 85)
    print("DB BENCHMARK - SYNC ISGEODatabase implementation")
    print("=" * 85)

    print("\n[Benchmarking SGEODatabaseSync...]")
    db_sync = SGEODatabaseSync()
    results_sync = run_benchmarks_sync(db_sync, data_dir)

    print()
    print("=" * 85)
    print("SYNC RESULTS (ns/query)")
    print("=" * 85)

    for r in results_sync:
        print(f"  {r.name:<40} | {r.ns_per_query:>10.0f} ns/q | {r.queries_per_sec:>8.0f} qps | {r.count:>6,}x")

    print()
    print("=" * 85)
    print("[DONE]")


if __name__ == "__main__":
    main()