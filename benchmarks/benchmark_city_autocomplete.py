"""
Benchmark for city autocomplete using Tantivy.
Tests performance and accuracy with various query patterns.
Uses same BooleanQuery + SHOULD approach as server.py.
"""

import random
import sqlite3
import time
from pathlib import Path

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir, get_sgeodb_path

# Global — same as server.py
_ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()


def load_index():
    """Load the index and register tokenizer."""
    index_path = str(get_tantivy_dir() / "city_index")
    index = tantivy.Index.open(index_path)
    index.register_tokenizer("ngram", _ngram_analyzer)
    return index


def text_to_ascii(text):
    """Normalize text for ASCII, uppercase."""
    if not text:
        return ""
    import unicodedata

    text = unicodedata.normalize("NFD", text.upper())
    text = "".join(c for c in text if c.isalnum() or c.isspace())
    text = " ".join(text.split())
    return text.strip()


def build_ngram_query(query_text: str, field_name: str, schema):
    """
    BooleanQuery with SHOULD (OR) per token — same logic as server.py.
    """
    tokens = _ngram_analyzer.analyze(query_text)
    if not tokens:
        return None

    subqueries = [(Occur.Should, tantivy.Query.term_query(schema, field_name, t)) for t in tokens]

    n = len(tokens)
    if n <= 3:
        min_match = 1
    elif n <= 8:
        min_match = n // 2
    else:
        min_match = n // 3 * 2

    return tantivy.Query.boolean_query(subqueries, min_match)


def search_cities(index, query, limit=10):
    """Search for cities using the autocomplete index."""
    query_normalized = text_to_ascii(query)
    if not query_normalized:
        return [], 0

    searcher = index.searcher()
    schema = index.schema

    tantivy_query = build_ngram_query(query_normalized, "city_search", schema)
    if tantivy_query is None:
        return [], 0

    results = searcher.search(tantivy_query, limit=limit)

    cities = []
    for score, doc_address in results.hits:
        doc = searcher.doc(doc_address)
        cities.append(
            {
                "city_code": doc.get_first("city_code"),
                "city_name": doc.get_first("city_name"),
                "state_code": doc.get_first("state_code"),
                "score": round(score, 4),
            }
        )

    return cities, len(cities)


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

    return city_normalized


def run_benchmark():
    """Run comprehensive benchmark."""
    print("=" * 60)
    print("CITY AUTOCOMPLETE BENCHMARK")
    print("=" * 60)

    print("\nLoading index...")
    start = time.time()
    index = load_index()
    load_time = time.time() - start
    print(f"Index loaded in {load_time:.3f}s")

    print("\nGetting test samples from database...")
    samples = get_test_samples(str(get_sgeodb_path()), 1000)
    print(f"Loaded {len(samples)} samples")

    test_cases = [
        ("Full name", lambda s: s[2]),
        ("Abbreviation", lambda s: mutate_query(s[2], "abbreviation")),
        ("Partial", lambda s: mutate_query(s[2], "partial")),
        ("First 2 chars", lambda s: s[2].split()[0][:2] if s[2] else ""),
        ("First 3 chars", lambda s: s[2].split()[0][:3] if s[2] else ""),
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

        for sample in samples[:100]:
            city_code, city_name, city_normalized = sample
            query = query_func(sample)

            if not query or len(query) < 2:
                continue

            try:
                start_time = time.time()
                results, count = search_cities(index, query, limit=10)
                query_time = time.time() - start_time

                total_time += query_time
                queries_tested += 1

                found = any(r["city_code"] == city_code for r in results)
                if found:
                    total_found += 1
                total_expected += 1

                if len(sample_results) < 5:
                    sample_results.append(
                        {
                            "query": query,
                            "expected": city_normalized,
                            "found": found,
                            "results_count": len(results),
                            "time_ms": round(query_time * 1000, 2),
                            "first_result": results[0]["city_name"] if results else None,
                        }
                    )

            except Exception as e:
                errors += 1

        avg_time = (total_time / queries_tested * 1000) if queries_tested > 0 else 0
        accuracy = (total_found / total_expected * 100) if total_expected > 0 else 0

        print(f"Queries tested: {queries_tested}")
        print(f"Errors: {errors}")
        print(f"Avg time per query: {avg_time:.2f}ms")
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
            f"{stats['avg_time_ms']:<10.2f} {stats['accuracy']:<10.1f}%"
        )

    all_times = []
    all_accuracies = []
    for stats in results_summary.values():
        all_times.append(stats["avg_time_ms"])
        all_accuracies.append(stats["accuracy"])

    print(f"\nOverall avg time: {sum(all_times) / len(all_times):.2f}ms")
    print(f"Overall avg accuracy: {sum(all_accuracies) / len(all_accuracies):.1f}%")

    return results_summary


if __name__ == "__main__":
    run_benchmark()
