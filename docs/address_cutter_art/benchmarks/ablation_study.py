"""Ablation study for AddressCutter article.

Runs the benchmark with fixed seed across multiple configurations
to measure the contribution of each component.
"""
import os
import random
import sqlite3
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from openaddrbr.core._address_cutter import AddressCutter
from benchmarks.noise_injector import inject_noise

SGEODB = "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db"
JSON_STATS = "data/address_stats.json"

LIMIT_SAMPLES = 100000
PROB_TOKEN_GLUING = 0.05
PROB_TYPING_STREET = 0.33
PROB_TYPING_NUMBER = 0.66
PROB_INJECT_NUMBER_IN_NEIGHBORHOOD = 0.80
SEED = 42


def build_queries(rows):
    """Pre-build all queries deterministically from seed."""
    random.seed(SEED)
    queries = []
    for row in rows:
        street = row["street_normalized"] or ""
        neighborhood = row["neighborhood_normalized"] or ""
        street_clean = street.strip()
        if not street_clean:
            continue

        street_clean, tags = inject_noise(street_clean)
        if not street_clean:
            continue

        rand_val = random.random()

        if rand_val < PROB_TYPING_STREET:
            tags.append("typing_street")
            street_tokens = street_clean.split()
            if not street_tokens:
                continue
            partial_street = " ".join(street_tokens[:-1])
            last_token = street_tokens[-1]
            cut_idx = random.randint(1, len(last_token))
            partial_last = last_token[:cut_idx]
            if partial_street:
                expected_street = f"{partial_street} {partial_last}"
            else:
                expected_street = partial_last
            query = expected_street

        elif rand_val < PROB_TYPING_NUMBER:
            tags.append("typing_number")
            house_number = str(random.randint(1, 9999))
            cut_idx = random.randint(1, len(house_number))
            partial_number = house_number[:cut_idx]
            space = "" if random.random() < PROB_TOKEN_GLUING else " "
            if not space:
                tags.append("token_gluing")
            query = f"{street_clean}{space}{partial_number}"
            expected_street = street_clean

        else:
            tags.append("typing_neighborhood")
            has_number = random.random() < PROB_INJECT_NUMBER_IN_NEIGHBORHOOD
            house_number = str(random.randint(1, 9999)) if has_number else ""
            neigh_tokens = neighborhood.strip().split()
            if not neigh_tokens:
                space = "" if random.random() < PROB_TOKEN_GLUING else " "
                if not space and has_number:
                    tags.append("token_gluing")
                query = f"{street_clean}{space}{house_number}" if has_number else street_clean
                expected_street = street_clean
            else:
                partial_neigh = " ".join(neigh_tokens[:-1])
                last_token = neigh_tokens[-1]
                cut_idx = random.randint(1, len(last_token))
                partial_last = last_token[:cut_idx]
                if partial_neigh:
                    partial_neigh += " " + partial_last
                else:
                    partial_neigh = partial_last
                if has_number:
                    space = "" if random.random() < PROB_TOKEN_GLUING else " "
                    if not space:
                        tags.append("token_gluing")
                    query = f"{street_clean}{space}{house_number} {partial_neigh}"
                else:
                    query = f"{street_clean} {partial_neigh}"
                expected_street = street_clean

        queries.append((query, expected_street, tags))
    return queries


def evaluate(cutter, queries):
    """Run evaluation, return (top1_acc, top3_acc, mrr, avg_ms)."""
    hits_at_1 = 0
    hits_at_3 = 0
    total = 0
    mrr_sum = 0.0
    total_latency = 0.0

    for query, expected_street, tags in queries:
        t0 = time.perf_counter()
        cuts = cutter.cut(query)
        t1 = time.perf_counter()
        total_latency += t1 - t0
        total += 1

        correct_position = -1
        for idx, hypothesis in enumerate(cuts):
            if hypothesis.street_part == expected_street:
                correct_position = idx
                break

        if correct_position != -1:
            rank = correct_position + 1
            if rank == 1:
                hits_at_1 += 1
            if rank <= 3:
                hits_at_3 += 1
            mrr_sum += 1.0 / rank

    acc1 = (hits_at_1 / total) * 100
    acc3 = (hits_at_3 / total) * 100
    mrr = mrr_sum / total
    avg_ms = (total_latency / total) * 1000
    return acc1, acc3, mrr, avg_ms


def first_digit_baseline(queries):
    """Naive baseline: split at the first digit character."""
    hits_at_1 = 0
    total = 0

    for query, expected_street, tags in queries:
        total += 1
        # Find first digit position
        split_pos = len(query)
        for i, c in enumerate(query):
            if c.isdigit():
                split_pos = i
                break
        street_guess = query[:split_pos].strip()
        if street_guess == expected_street:
            hits_at_1 += 1

    return (hits_at_1 / total) * 100


def run_ablation():
    print(f"Loading data (seed={SEED})...")
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT {LIMIT_SAMPLES}")
    rows = cursor.fetchall()
    conn.close()

    print("Building queries...")
    queries = build_queries(rows)
    print(f"Built {len(queries)} queries.\n")

    # Baseline: first digit split
    baseline_acc = first_digit_baseline(queries)
    print(f"{'Baseline (first digit)':40} | Top-1: {baseline_acc:6.2f}%")
    print("-" * 70)

    # Configurations: (name, kwargs)
    configs = [
        ("Modelo completo (default)", {}),
        ("Sem Decaimento Suave (hard floor)", {"use_kelly": False}),
        ("Sem Smart Split", {"gluing_threshold": None}),
    ]

    for name, kwargs in configs:
        cutter = AddressCutter(JSON_STATS, **kwargs)
        acc1, acc3, mrr, avg_ms = evaluate(cutter, queries)
        print(f"{name:40} | Top-1: {acc1:6.2f}% | Top-3: {acc3:6.2f}% | MRR: {mrr:.4f} | Avg: {avg_ms:.3f}ms")

    print("\nDone.")


if __name__ == "__main__":
    run_ablation()
