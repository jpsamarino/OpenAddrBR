"""
Encoder benchmark - measure throughput for Encoder.encode and Encoder.encode_batch.
"""

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path

from openaddrbr.core._encoder import Encoder
from openaddrbr.utils import normalize_text


@dataclass
class BenchmarkResult:
    name: str
    total_ms: float
    count: int
    ns_per_call: float
    items_per_sec: float  # calls/sec for single, streets/sec for batch


def load_data(path: Path, limit: int) -> list[str]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    # Normalize street names
    street_norms = []
    for item in raw[:limit]:
        street = item.get("place", {}).get("street", "")
        if street:
            street_norms.append(normalize_text(street))

    return street_norms


def benchmark_single(name: str, fn, data: list[str], warmup_runs: int = 3) -> BenchmarkResult:
    count = len(data)

    # Warmup
    for _ in range(warmup_runs):
        for item in data[: min(100, count)]:
            fn(item)

    # Benchmark
    t0 = time.perf_counter()
    for item in data:
        fn(item)
    elapsed_ns = (time.perf_counter() - t0) * 1_000_000_000

    ns_per_call = elapsed_ns / count if count > 0 else 0
    items_per_sec = 1_000_000_000 / ns_per_call if ns_per_call > 0 else 0

    return BenchmarkResult(
        name=name,
        total_ms=elapsed_ns / 1_000_000,
        count=count,
        ns_per_call=ns_per_call,
        items_per_sec=items_per_sec,
    )


def benchmark_batch(
    name: str, encoder: Encoder, data: list[str], batch_size: int, warmup_runs: int = 3
) -> BenchmarkResult:
    count = len(data)

    # Warmup
    for _ in range(warmup_runs):
        warmup_data = data[: min(100, count)]
        for i in range(0, len(warmup_data), batch_size):
            encoder.encode_batch(warmup_data[i : i + batch_size], batch_size)

    # Benchmark
    t0 = time.perf_counter()
    for i in range(0, count, batch_size):
        encoder.encode_batch(data[i : i + batch_size], batch_size)
    elapsed_ns = (time.perf_counter() - t0) * 1_000_000_000

    ns_per_batch = elapsed_ns / ((count + batch_size - 1) // batch_size) if count > 0 else 0
    total_ms = elapsed_ns / 1_000_000
    streets_per_sec = (count * 1_000) / total_ms if total_ms > 0 else 0

    return BenchmarkResult(
        name=name,
        total_ms=total_ms,
        count=count,
        ns_per_call=ns_per_batch,
        items_per_sec=streets_per_sec,
    )


def main():
    parser = argparse.ArgumentParser(description="Encoder benchmark")
    parser.add_argument("--limit", type=int, default=4000, help="Max items to load (default: 4000)")
    args = parser.parse_args()

    data_dir = Path(__file__).parent
    data_path = data_dir / "google_ref_lat_long.json"

    print(f"Loading data from {data_path}...")
    street_norms = load_data(data_path, args.limit)
    print(f"Loaded {len(street_norms):,} street names")

    if len(street_norms) == 0:
        print("No data loaded. Exiting.")
        return

    encoder = Encoder()
    batch_sizes = [2, 4, 8, 16, 32, 64]

    print()
    print("=" * 90)
    print("ENCODER BENCHMARK")
    print("=" * 90)
    print(f"Data: {data_path.name}")
    print(f"Items: {len(street_norms):,}")
    print(f"Batch sizes: {batch_sizes}")
    print()

    # encode (single)
    print("encode (single):")
    print(f"  {'name':<40} | {'ns/call':>12} | {'calls/sec':>12} | {'count':>8}")
    print("-" * 78)

    r_single = benchmark_single("encode", encoder.encode, street_norms)
    print(
        f"  {r_single.name:<40} | {r_single.ns_per_call:>12.0f} | {r_single.items_per_sec:>12.0f} | {r_single.count:>8,}"
    )

    print()

    # encode_batch (batch sizes)
    print("encode_batch (batch sizes):")
    print(f"  {'name':<40} | {'batch':>6} | {'ns/batch':>12} | {'streets/sec':>12} | {'count':>8}")
    print("-" * 90)

    best_streets_sec = 0
    best_batch = 0
    results = []

    for batch_size in batch_sizes:
        # Skip if batch_size > data length
        if batch_size > len(street_norms):
            print(f"  encode_batch (bs={batch_size:<3}) | skipped (data too small)")
            continue

        name = f"encode_batch (bs={batch_size})"
        r = benchmark_batch(name, encoder, street_norms, batch_size)
        results.append(r)
        print(
            f"  {r.name:<40} | {batch_size:>6} | {r.ns_per_call:>12.0f} | {r.items_per_sec:>12.0f} | {r.count:>8,}"
        )

        if r.items_per_sec > best_streets_sec:
            best_streets_sec = r.items_per_sec
            best_batch = batch_size

    print()
    print("=" * 90)

    if best_batch > 0:
        print(f"Best batch size: {best_batch} ({best_streets_sec:.0f} streets/sec)")

    print("[DONE]")


if __name__ == "__main__":
    main()
