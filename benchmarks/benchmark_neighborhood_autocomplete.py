"""
Benchmark for neighborhood autocomplete using LocationSuggestions.
Tests performance and accuracy with various query patterns.
"""

import json
import random
import time
from pathlib import Path

from openaddrbr.services._suggestions import LocationSuggestions

SAMPLES_LIMIT = 10000  # Number of samples to test per case (10k for cache warming)

# Shared suggestions instance
_suggestions = LocationSuggestions()


def load_samples():
    """Load benchmark samples from JSON."""
    samples_path = Path(__file__).parent / "benchmark_neighborhoods.json"
    with open(samples_path, "r", encoding="utf-8") as f:
        return json.load(f)


def mutate_query(neighborhood_normalized, mutation_type="random"):
    """Create mutated versions of neighborhood name to simulate typos/abbreviations."""
    words = neighborhood_normalized.split()

    if mutation_type == "abbreviation":
        # Keep first 2-3 chars of each word
        return " ".join(w[: min(3, len(w))] for w in words if len(w) > 1)

    elif mutation_type == "typo":
        # Replace random letters
        result = []
        for w in words:
            if len(w) > 2 and random.random() > 0.5:
                idx = random.randint(0, len(w) - 1)
                w = w[:idx] + random.choice("aeioubcdefghjklmnopqrstuvwxyz") + w[idx + 1 :]
            result.append(w)
        return " ".join(result)

    elif mutation_type == "partial":
        # Take only first word partially
        if words:
            return words[0][:2] + " " + " ".join(w[:3] for w in words[1:3] if len(w) > 3)
        return ""

    return neighborhood_normalized


def run_benchmark():
    """Run comprehensive benchmark."""
    print("=" * 60)
    print("NEIGHBORHOOD AUTOCOMPLETE BENCHMARK")
    print("=" * 60)

    print("\nLoading benchmark samples...")
    samples = load_samples()
    print(f"Loaded {len(samples)} samples from {len(set(s['city_code'] for s in samples))} cities")

    test_cases = [
        ("Full name", lambda s: s["neighborhood_normalized"]),
        (
            "Abbreviation",
            lambda s: mutate_query(s["neighborhood_normalized"], "abbreviation"),
        ),
        ("Partial", lambda s: mutate_query(s["neighborhood_normalized"], "partial")),
        (
            "First 2 chars",
            lambda s: (
                s["neighborhood_normalized"].split()[0][:2] if s["neighborhood_normalized"] else ""
            ),
        ),
        (
            "First 3 chars",
            lambda s: (
                s["neighborhood_normalized"].split()[0][:3] if s["neighborhood_normalized"] else ""
            ),
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
            neighborhood_normalized = sample["neighborhood_normalized"]
            city_code = sample["city_code"]
            neighborhood_name = sample["neighborhood_name"]

            query = query_func(sample)

            if not query or len(query) < 2:
                continue

            try:
                start_time = time.time()
                results = _suggestions.search_neighborhoods(query, city_code, limit=10)
                query_time = time.time() - start_time

                total_time += query_time
                queries_tested += 1

                # Check if expected neighborhood is in results
                found = any(
                    r.neighborhood_normalized[:20] == neighborhood_normalized[:20]
                    for r in results
                )
                if found:
                    total_found += 1
                total_expected += 1

                if len(sample_results) < 5:
                    sample_results.append(
                        {
                            "query": query,
                            "expected": neighborhood_normalized,
                            "found": found,
                            "results_count": len(results),
                            "time_ms": round(query_time * 1000, 2),
                            "first_result": (results[0].neighborhood_name if results else None),
                        }
                    )

            except Exception as e:
                errors += 1

        avg_time = (total_time / queries_tested * 1000) if queries_tested > 0 else 0
        accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0

        print(f"Queries tested: {queries_tested}")
        print(f"Errors: {errors}")
        print(f"Avg time per query: {avg_time:.4f}ms")
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
            "accuracy": accuracy,
            "errors": errors,
        }

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'Test':<20} {'Queries':<10} {'Avg ms':<10} {'Accuracy':<10}")
    print("-" * 50)
    for test_name, stats in results_summary.items():
        print(
            f"{test_name:<20} {stats['queries']:<10} "
            f"{stats['avg_time_ms']:<10.4f} {stats['accuracy']:<10.1f}%"
        )

    all_times = []
    all_accuracies = []
    for stats in results_summary.values():
        all_times.append(stats["avg_time_ms"])
        all_accuracies.append(stats["accuracy"])

    print(f"\nOverall avg time: {sum(all_times) / len(all_times):.4f}ms")
    print(f"Overall avg accuracy: {sum(all_accuracies) / len(all_accuracies):.1f}%")

    return results_summary


if __name__ == "__main__":
    run_benchmark()