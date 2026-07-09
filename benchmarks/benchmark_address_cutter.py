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


def run_benchmark():
    print(f"Loading AddressCutter with stats from {JSON_STATS}...")
    cutter = AddressCutter(JSON_STATS)

    print(f"Connecting to database {SGEODB}...")
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch a sample of 100,000 random addresses to evaluate
    print("Fetching 100,000 samples...")
    cursor.execute(
        "SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT 100000"
    )
    rows = cursor.fetchall()

    hits_at_1 = 0
    hits_at_3 = 0
    total = 0
    mrr_sum = 0.0

    total_latency_sec = 0.0

    for row in rows:
        street = row["street_normalized"] or ""
        neighborhood = row["neighborhood_normalized"] or ""

        street_clean = street.strip()
        if not street_clean:
            continue

        # Simulating Autocomplete Typing
        # 33% chance typing street
        # 33% chance typing house number
        # 33% chance typing neighborhood
        rand_val = random.random()

        if rand_val < 0.33:
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

        elif rand_val < 0.66:
            # Typing house number: "RUA JOSE COSTA 12"
            house_number = str(random.randint(1, 9999))
            cut_idx = random.randint(1, len(house_number))
            partial_number = house_number[:cut_idx]

            query = f"{street_clean} {partial_number}"
            expected_street = street_clean

        else:
            # Typing neighborhood: "RUA JOSE COSTA 123 ALV"
            # We inject a full house number 80% of the time here
            has_number = random.random() < 0.8
            house_number = str(random.randint(1, 9999)) if has_number else ""

            neigh_tokens = neighborhood.strip().split()
            if not neigh_tokens:
                # if no neighborhood in db, fallback to just number
                query = f"{street_clean} {house_number}" if has_number else street_clean
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
                    query = f"{street_clean} {house_number} {partial_neigh}"
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
            if rank <= 3:
                hits_at_3 += 1
            mrr_sum += 1.0 / rank

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


if __name__ == "__main__":
    run_benchmark()
