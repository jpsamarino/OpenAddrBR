"""
Vector Search benchmark - measure throughput for search phase only.

Encode is measured separately in benchmark_encoder.py.
This benchmark focuses only on the vector search pipeline.
"""

import argparse
import json
import sys
import time
from io import StringIO
from pathlib import Path

from openaddrbr.data._db import get_city_info_from_db
from openaddrbr.services._encoder import _encode_streets_batch
from openaddrbr.services._vector_search import _search_by_embedding
from openaddrbr.utils import normalize_text


def load_addresses(
    path: Path, limit: int, city_filter: str | None = None
) -> list[dict]:
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Shuffle to get random sample across the file
    import random
    random.shuffle(records)

    addresses = []
    for rec in records:
        place = rec.get("place") or {}
        if city_filter:
            if place.get("city", "").upper() != city_filter.upper():
                continue
        addresses.append(rec)
        if limit and len(addresses) >= limit:
            break

    return addresses


def run_search_benchmark(addresses: list[dict], batch_size: int = 32) -> dict:
    items = []
    for rec in addresses:
        place = rec.get("place") or {}
        city_info = get_city_info_from_db(
            place.get("city", ""), place.get("state", "")
        )
        if not city_info:
            continue

        items.append(
            {
                "street_norm": normalize_text(place.get("street", "")),
                "neighborhood_norm": normalize_text(
                    place.get("neighborhood", "")
                ),
                "city_code": city_info.city_code,
            }
        )

    if not items:
        return {"error": "No valid addresses"}

    # Encode all street names (suppress stdout/stderr from sentence_transformers)
    old_stderr = sys.stderr
    sys.stderr = StringIO()

    embeddings = []
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]
        emb_batch = _encode_streets_batch(
            [x["street_norm"] for x in batch], batch_size=batch_size
        )
        embeddings.extend(emb_batch)

    sys.stderr = old_stderr

    # Search phase
    search_start = time.perf_counter()
    results = []
    for i, item in enumerate(items):
        cluster = _search_by_embedding(
            item["city_code"],
            embeddings[i],
            item["street_norm"],
            item["neighborhood_norm"],
        )
        results.append(cluster is not None)
    search_elapsed = time.perf_counter() - search_start

    total = len(items)
    return {
        "items": total,
        "ms": search_elapsed * 1000,
        "ms_per_item": (search_elapsed * 1000) / total,
        "qps": total / search_elapsed if search_elapsed > 0 else 0,
        "found": sum(results),
        "found_pct": sum(results) / total * 100,
    }

    # Search phase
    search_start = time.perf_counter()
    results = []
    for i, item in enumerate(items):
        cluster = _search_by_embedding(
            item["city_code"],
            embeddings[i],
            item["street_norm"],
            item["neighborhood_norm"],
        )
        results.append(cluster is not None)
    search_elapsed = time.perf_counter() - search_start

    total = len(items)
    return {
        "items": total,
        "ms": search_elapsed * 1000,
        "ms_per_item": (search_elapsed * 1000) / total,
        "qps": total / search_elapsed if search_elapsed > 0 else 0,
        "found": sum(results),
        "found_pct": sum(results) / total * 100,
    }


def main():
    parser = argparse.ArgumentParser(description="Vector Search benchmark")
    parser.add_argument(
        "--limit", type=int, default=1000, help="Max addresses (default: 1000)"
    )
    parser.add_argument(
        "--batch-size", type=int, default=32, help="Batch size (default: 32)"
    )
    parser.add_argument(
        "--city", type=str, default=None, help="Filter by city (e.g., SAO PAULO)"
    )
    parser.add_argument(
        "--all", action="store_true", help="Run all city tests"
    )
    args = parser.parse_args()

    data_path = Path(__file__).parent / "google_ref_lat_long.json"

    print("=" * 65)
    print("VECTOR SEARCH BENCHMARK")
    print("=" * 65)
    print(f"Data:       {data_path.name}")
    print(f"Batch size: {args.batch_size}")
    print()
    print(f"{'Test':<20} | {'Items':>6} | {'ms':>7} | {'ms/item':>8} | {'QPS':>7} | {'Found':>7}")
    print("-" * 65)

    tests = []

    if args.all:
        # Multi-city test first
        addrs = load_addresses(data_path, args.limit)
        if len(addrs) >= 10:
            stats = run_search_benchmark(addrs, batch_size=args.batch_size)
            tests.append(("Multi-city", stats))

        # Single city tests
        for city in ["SAO PAULO", "RIO DE JANEIRO", "BRASILIA"]:
            addrs = load_addresses(data_path, args.limit, city_filter=city)
            if len(addrs) < 10:
                continue
            stats = run_search_benchmark(addrs, batch_size=args.batch_size)
            tests.append((f"{city} only", stats))
    else:
        addrs = load_addresses(
            data_path, args.limit, city_filter=args.city
        )
        if not addrs:
            print("No addresses found")
            return
        stats = run_search_benchmark(addrs, batch_size=args.batch_size)
        city_name = args.city if args.city else "Multi-city"
        tests.append((city_name, stats))

    for name, stats in tests:
        print(
            f"{name:<20} | "
            f"{stats['items']:>6,} | "
            f"{stats['ms']:>7.0f} | "
            f"{stats['ms_per_item']:>8.2f} | "
            f"{stats['qps']:>7.1f} | "
            f"{stats['found_pct']:>6.1f}%"
        )

    print("=" * 65)


if __name__ == "__main__":
    main()