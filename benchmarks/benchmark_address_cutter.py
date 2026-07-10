import os
import random
import sqlite3
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from openaddrbr.core._address_cutter import AddressCutter

SGEODB = "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db"
JSON_STATS = "data/address_stats.json"

import time
from noise_injector import inject_noise

# Benchmark Configuration
LIMIT_SAMPLES = 100000
PROB_TOKEN_GLUING = 0.05
PROB_TYPING_STREET = 0.33
PROB_TYPING_NUMBER = 0.66
PROB_INJECT_NUMBER_IN_NEIGHBORHOOD = 0.80

def run_benchmark():
    print(f"Loading AddressCutter with stats from {JSON_STATS}...")
    cutter = AddressCutter(JSON_STATS)

    print(f"Connecting to database {SGEODB}...")
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch a sample of random addresses to evaluate
    print(f"Fetching {LIMIT_SAMPLES} samples...")
    cursor.execute(
        f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT {LIMIT_SAMPLES}"
    )
    rows = cursor.fetchall()

    from collections import defaultdict

    hits_at_1 = 0
    hits_at_3 = 0
    total = 0
    mrr_sum = 0.0
    
    stats_by_tag = defaultdict(lambda: {"total": 0, "hits_at_1": 0, "hits_at_3": 0})

    total_latency_sec = 0.0

    for row in rows:
        street = row["street_normalized"] or ""
        neighborhood = row["neighborhood_normalized"] or ""

        street_clean = street.strip()
        if not street_clean:
            continue
            
        street_clean, tags = inject_noise(street_clean)
        if not street_clean:
            continue

        # Simulating Autocomplete Typing
        rand_val = random.random()

        if rand_val < PROB_TYPING_STREET:
            tags.append("typing_street")
            # Typing street: "RUA JOSE COS"
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
            # Typing house number: "RUA JOSE COSTA 12"
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
            # Typing neighborhood: "RUA JOSE COSTA 123 ALV"
            # We inject a full house number based on the probability
            has_number = random.random() < PROB_INJECT_NUMBER_IN_NEIGHBORHOOD
            house_number = str(random.randint(1, 9999)) if has_number else ""

            neigh_tokens = neighborhood.strip().split()
            if not neigh_tokens:
                # if no neighborhood in db, fallback to just number
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

        # Start timing
        t0 = time.perf_counter()
        cuts = cutter.cut(query)
        t1 = time.perf_counter()

        total_latency_sec += t1 - t0
        total += 1

        # Check where the correct street boundary appeared
        correct_position = -1
        for idx, hypothesis in enumerate(cuts):
            if hypothesis.street_part == expected_street:
                correct_position = idx
                break

        if correct_position != -1:
            rank = correct_position + 1
            if rank == 1:
                hits_at_1 += 1
                for tag in tags:
                    stats_by_tag[tag]["hits_at_1"] += 1
            if rank <= 3:
                hits_at_3 += 1
                for tag in tags:
                    stats_by_tag[tag]["hits_at_3"] += 1
            mrr_sum += 1.0 / rank

        for tag in tags:
            stats_by_tag[tag]["total"] += 1

    print(f"\n--- Benchmark Results ({total} queries) ---")
    print(f"Top 1 Accuracy: {(hits_at_1 / total) * 100:.2f}%")
    print(f"Top 3 Accuracy: {(hits_at_3 / total) * 100:.2f}%")
    print(f"Mean Reciprocal Rank (MRR): {mrr_sum / total:.4f}")

    avg_ms = (total_latency_sec / total) * 1000
    qps = total / total_latency_sec
    print(f"\n--- Performance Metrics ---")
    print(f"Total Inference Time: {total_latency_sec:.4f}s")
    print(f"Average Latency per Query: {avg_ms:.4f} ms")
    print(f"Throughput (QPS): {qps:.0f} queries/sec")

    print("\n--- Breakdown by Noise Type ---")
    # Sort tags by total samples descending
    sorted_tags = sorted(stats_by_tag.items(), key=lambda x: x[1]["total"], reverse=True)
    for tag, stats in sorted_tags:
        t = stats["total"]
        if t == 0:
            continue
        acc1 = (stats["hits_at_1"] / t) * 100
        acc3 = (stats["hits_at_3"] / t) * 100
        print(f"[{tag:20}] Top 1: {acc1:5.2f}% | Top 3: {acc3:5.2f}% (Total: {t})")


if __name__ == "__main__":
    run_benchmark()
