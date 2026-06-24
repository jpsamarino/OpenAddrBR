"""
Benchmark for street autocomplete comparing search_streets vs autocomplete_street.
Tests performance and accuracy with various query patterns.
Uses normalize_text for case-insensitive accuracy comparison.
"""

import json
import random
import time
from pathlib import Path

from openaddrbr.core._location_search import LocationSearch
from openaddrbr.utils import normalize_text

SAMPLES_LIMIT = 10000

_suggestions = LocationSearch()


def load_samples():
    """Load benchmark samples from JSON."""
    samples_path = Path(__file__).parent / "benchmark_streets.json"
    with open(samples_path, "r", encoding="utf-8") as f:
        return json.load(f)


def mutate_query(street_normalized, mutation_type="random"):
    """Create mutated versions of street name to simulate typos."""
    words = street_normalized.split()

    if mutation_type == "abbreviation":
        return " ".join(w[: min(3, len(w))] for w in words if len(w) > 1)
    elif mutation_type == "typo":
        result = []
        for w in words:
            if len(w) > 2 and random.random() > 0.5:
                idx = random.randint(0, len(w) - 1)
                w = w[:idx] + random.choice("aeioubcdefghjklmnopqrstuvwxyz") + w[idx + 1 :]
            result.append(w)
        return " ".join(result)
    elif mutation_type == "partial":
        if words:
            return words[0][:2] + " " + " ".join(w[:3] for w in words[1:3] if len(w) > 3)
        return ""

    return street_normalized


def check_accuracy(results, expected_normalized, result_type="street_segment"):
    """Check if expected street is in results using normalize_text for comparison."""
    expected_norm = normalize_text(expected_normalized)

    for r in results:
        if result_type == "string":
            result_norm = normalize_text(r)
        else:
            result_norm = normalize_text(getattr(r, "street_normalized", ""))
        if result_norm[:20] == expected_norm[:20]:
            return True
    return False


def run_benchmark(mode="search_autocomplete"):
    """Run benchmark with different modes.

    Modes:
        - "search_normal": search_streets with autocomplete_query=False
        - "search_autocomplete": search_streets with autocomplete_query=True
        - "autocomplete_street": new autocomplete_street method (pure Tantivy, no SQLite)
    """
    mode_labels = {
        "search_normal": "SEARCH_STREETS (ngram)",
        "search_autocomplete": "SEARCH_STREETS (autocomplete)",
        "autocomplete_street": "AUTOCOMPLETE_STREET (pure Tantivy)",
    }
    label = mode_labels.get(mode, mode)
    print(f"\n{'=' * 60}")
    print(f"BENCHMARK - {label}")
    print(f"{'=' * 60}")

    print("\nLoading benchmark samples...")
    samples = load_samples()
    print(f"Loaded {len(samples)} samples from {len(set(s['city_code'] for s in samples))} cities")

    test_cases = [
        ("Full name", lambda s: s["street_normalized"]),
        ("Abbreviation", lambda s: mutate_query(s["street_normalized"], "abbreviation")),
        ("Partial", lambda s: mutate_query(s["street_normalized"], "partial")),
        (
            "First 2 chars",
            lambda s: s["street_normalized"].split()[0][:2] if s["street_normalized"] else "",
        ),
        (
            "First 3 chars",
            lambda s: s["street_normalized"].split()[0][:3] if s["street_normalized"] else "",
        ),
    ]

    results_summary = {}

    for test_name, query_func in test_cases:
        print(f"\n{'=' * 50}")
        print(f"Test: {test_name}")
        print(f"{'=' * 50}")

        total_time = 0
        total_found = 0
        total_expected = 0
        queries_tested = 0

        errors = 0
        sample_results = []

        for sample in samples[:SAMPLES_LIMIT]:
            street_normalized = sample["street_normalized"]
            city_code = sample["city_code"]

            query = query_func(sample)

            if not query or len(query) < 2:
                continue

            found = False  # Reset for each iteration
            results_count = 0
            first_result = None

            try:
                # Time only the search call (not accuracy check)
                start_time = time.time()

                if mode == "autocomplete_street":
                    results = _suggestions.autocomplete_street(
                        city_code=city_code, query=query, limit=10
                    )
                    results_count = len(results)
                    first_result = results[0] if results else None
                else:
                    autocomplete = (mode == "search_autocomplete")
                    results = _suggestions.search_streets(
                        query=query, city_code=city_code, limit=10, autocomplete_query=autocomplete
                    )
                    results_count = len(results)
                    first_result = results[0].street_name if results else None

                query_time = time.time() - start_time

                # Accuracy check OUTSIDE of timing
                if mode == "autocomplete_street":
                    found = check_accuracy(results, street_normalized, result_type="string")
                else:
                    found = check_accuracy(results, street_normalized, result_type="street_segment")

                total_time += query_time
                queries_tested += 1

                if found:
                    total_found += 1
                total_expected += 1

                if len(sample_results) < 5:
                    sample_results.append(
                        {
                            "query": query,
                            "expected": street_normalized,
                            "found": found,
                            "results_count": results_count,
                            "time_ms": round(query_time * 1000, 2),
                            "first_result": first_result,
                        }
                    )

            except Exception:
                errors += 1

        avg_time = (total_time / queries_tested * 1000) if queries_tested > 0 else 0
        accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0
        qps = (queries_tested / total_time) if total_time > 0 else 0

        print(f"Queries tested: {queries_tested}")
        print(f"Errors: {errors}")
        print(f"Avg time per query: {avg_time:.4f}ms | QPS: {qps:.0f}")
        print(f"Accuracy (expected in top 10): {accuracy:.1f}%")

        print("\nSample queries:")
        for sr in sample_results:
            status = "OK" if sr["found"] else "FAIL"
            first = sr.get("first_result", "N/A")
            print(
                f"  {status} '{sr['query']}' -> expected: {sr['expected']}, "
                f"first: {first}, got {sr['results_count']} results in {sr['time_ms']}ms"
            )

        results_summary[test_name] = {
            "queries": queries_tested,
            "avg_time_ms": avg_time,
            "qps": qps,
            "accuracy": accuracy,
            "errors": errors,
        }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Test':<20} {'Queries':<10} {'Avg ms':<10} {'QPS':<10} {'Accuracy':<10}")
    print("-" * 60)
    for test_name, stats in results_summary.items():
        print(
            f"{test_name:<20} {stats['queries']:<10} "
            f"{stats['avg_time_ms']:<10.4f} {stats['qps']:<10.0f} {stats['accuracy']:<10.1f}%"
        )

    all_times = []
    all_accuracies = []
    for stats in results_summary.values():
        all_times.append(stats["avg_time_ms"])
        all_accuracies.append(stats["accuracy"])

    overall_avg = sum(all_times) / len(all_times)
    overall_qps = 1000 / overall_avg if overall_avg > 0 else 0
    print(f"\nOverall avg time: {overall_avg:.4f}ms")
    print(f"Overall avg QPS: {overall_qps:.0f}")
    print(f"Overall avg accuracy: {sum(all_accuracies) / len(all_accuracies):.1f}%")

    return results_summary, overall_avg, overall_qps


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("COMPARING 3 MODES")
    print("=" * 60)

    results_normal, avg_normal, qps_normal = run_benchmark(mode="search_normal")
    results_auto, avg_auto, qps_auto = run_benchmark(mode="search_autocomplete")
    results_autocomplete, avg_autocomplete, qps_autocomplete = run_benchmark(mode="autocomplete_street")

    print("\n" + "=" * 60)
    print("COMPARISON SUMMARY")
    print("=" * 60)
    print(f"{'Test':<20} {'NGRAM ms':<12} {'QPS':<10} {'AUTO ms':<12} {'QPS':<10} {'PURE_TANTIVY ms':<16} {'QPS':<10}")
    print("-" * 100)
    for test_name in results_normal.keys():
        rn = results_normal[test_name]
        ra = results_auto[test_name]
        rc = results_autocomplete[test_name]
        print(
            f"{test_name:<20} {rn['avg_time_ms']:<12.4f} {rn['qps']:<10.0f} "
            f"{ra['avg_time_ms']:<12.4f} {ra['qps']:<10.0f} "
            f"{rc['avg_time_ms']:<16.4f} {rc['qps']:<10.0f}"
        )

    print("\n" + "=" * 60)
    print("OVERALL COMPARISON")
    print("=" * 60)
    print(f"search_streets (ngram)           - Avg: {avg_normal:.4f}ms | {qps_normal:.0f} QPS")
    print(f"search_streets (autocomplete)     - Avg: {avg_auto:.4f}ms | {qps_auto:.0f} QPS")
    print(f"autocomplete_street (pure Tantivy) - Avg: {avg_autocomplete:.4f}ms | {qps_autocomplete:.0f} QPS")
    print()
    print(f"Speedup autocomplete_street vs search_streets (ngram): {avg_normal/avg_autocomplete:.2f}x")
    print(f"Speedup autocomplete_street vs search_streets (auto): {avg_auto/avg_autocomplete:.2f}x")
