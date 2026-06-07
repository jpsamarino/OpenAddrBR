"""
Benchmark para comparar search_cities com min_match=1 vs lógica padrão.
"""

import sqlite3
import time

from openaddrbr.core._location_search import LocationSearch
from openaddrbr.core.env import get_sgeodb_path


def get_test_samples(db_path, n=1000):
    """Get random city samples from database for testing."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT city_code, city_name, city_normalized FROM cities ORDER BY RANDOM() LIMIT ?", (n,)
    )
    samples = cursor.fetchall()
    conn.close()
    return samples


def mutate_query(city_normalized, mutation_type="random"):
    """Create mutated versions of city name to simulate typos/abbreviations."""
    words = city_normalized.split()

    if mutation_type == "abbreviation":
        return " ".join(w[: min(3, len(w))] for w in words if len(w) > 1)

    elif mutation_type == "partial":
        if words:
            return words[0][:2] + " " + " ".join(w[:3] for w in words[1:3] if len(w) > 3)
        return ""

    return city_normalized


def run_benchmark(suggestions, samples, test_name, query_func, iterations=1):
    """Run benchmark for a specific configuration."""
    total_time = 0
    total_found = 0
    total_expected = 0
    queries_tested = 0

    for _ in range(iterations):
        for sample in samples[:100]:
            city_code, city_name, city_normalized = sample
            query = query_func(sample)

            if not query or len(query) < 2:
                continue

            start_time = time.time()
            results = suggestions.search_cities(query, limit=10)
            query_time = time.time() - start_time

            total_time += query_time
            queries_tested += 1

            found = any(r.city_code == city_code for r in results)
            if found:
                total_found += 1
            total_expected += 1

    avg_time = (total_time / queries_tested * 1000) if queries_tested > 0 else 0
    accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0

    return {
        "test_name": test_name,
        "queries": queries_tested,
        "avg_time_ms": avg_time,
        "accuracy": accuracy,
    }


def main():
    print("=" * 70)
    print("BENCHMARK: search_cities - min_match=1 vs Default")
    print("=" * 70)

    print("\nGetting test samples from database...")
    samples = get_test_samples(str(get_sgeodb_path()), 1000)
    print(f"Loaded {len(samples)} samples")

    suggestions = LocationSearch()

    test_cases = [
        ("Full name", lambda s: s[2]),
        ("Abbreviation", lambda s: mutate_query(s[2], "abbreviation")),
        ("Partial", lambda s: mutate_query(s[2], "partial")),
        ("First 2 chars", lambda s: s[2].split()[0][:2] if s[2] else ""),
        ("First 3 chars", lambda s: s[2].split()[0][:3] if s[2] else ""),
    ]

    results_summary = {}

    for test_name, query_func in test_cases:
        print(f"\n{'=' * 60}")
        print(f"Test: {test_name}")
        print(f"{'=' * 60}")

        # Run 2 iterations
        result = run_benchmark(suggestions, samples, test_name, query_func, iterations=2)

        print(f"Queries tested: {result['queries']}")
        print(f"Avg time per query: {result['avg_time_ms']:.2f}ms")
        print(f"Accuracy (expected in top 10): {result['accuracy']:.1f}%")

        results_summary[test_name] = result

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"{'Test':<20} {'Queries':<10} {'Avg ms':<10} {'Accuracy':<10}")
    print("-" * 50)
    for test_name, stats in results_summary.items():
        print(
            f"{test_name:<20} {stats['queries']:<10} "
            f"{stats['avg_time_ms']:<10.2f} {stats['accuracy']:<10.1f}%"
        )

    all_times = [s["avg_time_ms"] for s in results_summary.values()]
    all_accuracies = [s["accuracy"] for s in results_summary.values()]

    print(f"\nOverall avg time: {sum(all_times) / len(all_times):.2f}ms")
    print(f"Overall avg accuracy: {sum(all_accuracies) / len(all_accuracies):.1f}%")

    return results_summary


if __name__ == "__main__":
    main()