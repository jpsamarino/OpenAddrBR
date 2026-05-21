"""
Memory benchmark for usearch index loading.
Measures REAL RAM usage (RSS) using psutil.

Usage:
    python benchmarks/benchmark_memory.py
"""

import json
import os
from pathlib import Path

import psutil

from openaddrbr.data._sql_db import SQLDB as Database
from openaddrbr.core._env import get_usearch_dir
from openaddrbr.data._usearch import UsearchIndex


def get_city_codes(limit=None):
    """Get distinct city codes from benchmark data."""
    data_path = Path(__file__).parent / "google_ref_lat_long.json"
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db = Database()
    codes = set()
    for d in data:
        place = d.get("place", {})
        ci = db.get_city_info_from_db(place.get("city", ""), place.get("state", ""))
        if ci:
            codes.add(ci.city_code)
        if limit and len(codes) >= limit:
            break

    return sorted(codes)


def get_file_sizes(codes):
    """Get total disk size for usearch indices."""
    usearch_dir = get_usearch_dir()
    total = 0
    for code in codes:
        path = usearch_dir / f"{code}.usearch"
        if path.exists():
            total += path.stat().st_size
    return total


def main():
    process = psutil.Process(os.getpid())

    print("=" * 60)
    print("MEMORY BENCHMARK - Real RAM (RSS)")
    print("=" * 60)
    print()

    # Get all city codes
    codes = get_city_codes()
    print(f"Total distinct cities in dataset: {len(codes)}")

    disk_size = get_file_sizes(codes) / 1024 / 1024
    avg_size = disk_size / len(codes) if codes else 0
    print(f"Total on disk (all indices): {disk_size:.1f} MB")
    print(f"Avg per index: {avg_size:.2f} MB")
    print()

    # Test with different counts
    test_sizes = [10, 50, 100, 500, 1000]

    for size in test_sizes:
        UsearchIndex.clear_cache()

        mem_before = process.memory_info().rss / 1024 / 1024
        loaded = 0

        for code in codes[:size]:
            UsearchIndex.get(code)
            loaded += 1

        mem_after = process.memory_info().rss / 1024 / 1024
        delta = mem_after - mem_before
        cache_size = len(UsearchIndex._cache)

        print(f"  Load {loaded} indices:")
        print(f"    RAM before:   {mem_before:.1f} MB")
        print(f"    RAM after:    {mem_after:.1f} MB")
        print(f"    Delta (RSS):  {delta:+.1f} MB")
        print(f"    Cache size:   {cache_size}")
        print()

    # Load ALL
    print("  Load ALL (2449) indices:")
    UsearchIndex.clear_cache()
    mem_before = process.memory_info().rss / 1024 / 1024

    for code in codes:
        UsearchIndex.get(code)

    mem_after = process.memory_info().rss / 1024 / 1024
    delta = mem_after - mem_before
    cache_size = len(UsearchIndex._cache)

    print(f"    RAM before:   {mem_before:.1f} MB")
    print(f"    RAM after:    {mem_after:.1f} MB")
    print(f"    Delta (RSS):  {delta:+.1f} MB")
    print(f"    Cache size:   {cache_size}")
    print()

    print("=" * 60)
    print("NOTE: mmap with view=True means OS pages are loaded on-demand.")
    print("RSS grows as pages are accessed. Unused pages stay on disk.")
    print("=" * 60)


if __name__ == "__main__":
    main()