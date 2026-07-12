import os
import random
import sqlite3
import sys
import time
from collections import defaultdict
import spacy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from benchmarks.noise_injector import inject_noise

SGEODB = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
LIMIT_SAMPLES = 100000
PROB_TYPING_STREET = 0.33
PROB_TYPING_NUMBER = 0.66

def run_benchmark(model_path="models/crf_poc/model-best"):
    print(f"Loading CRF (spaCy) model from {model_path}...")
    try:
        nlp = spacy.load(model_path)
    except OSError:
        print("Model not found, skipping benchmark run.")
        return

    if not os.path.exists(SGEODB):
        print(f"Error: Database not found at {SGEODB}")
        sys.exit(1)

    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT {LIMIT_SAMPLES}")
    rows = cursor.fetchall()

    hits_at_1 = 0
    total = 0
    stats_by_tag = defaultdict(lambda: {"total": 0, "hits_at_1": 0})
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

        rand_val = random.random()
        if rand_val < PROB_TYPING_STREET:
            tags.append("typing_street")
            query = street_clean
            expected_street = street_clean
        elif rand_val < PROB_TYPING_NUMBER:
            tags.append("typing_number")
            query = f"{street_clean} 12"
            expected_street = street_clean
        else:
            tags.append("typing_neighborhood")
            query = f"{street_clean} 123 {neighborhood}"
            expected_street = street_clean

        t0 = time.perf_counter()
        doc = nlp(query)
        t1 = time.perf_counter()

        total_latency_sec += t1 - t0
        total += 1

        pred_street = ""
        for ent in doc.ents:
            if ent.label_ == "STREET":
                pred_street = ent.text
                break
        
        if pred_street == expected_street or expected_street in pred_street:
            hits_at_1 += 1
            for tag in tags:
                stats_by_tag[tag]["hits_at_1"] += 1
                
        for tag in tags:
            stats_by_tag[tag]["total"] += 1

    print(f"\n--- CRF Benchmark Results ({total} queries) ---")
    if total > 0:
        print(f"Top 1 Accuracy: {(hits_at_1 / total) * 100:.2f}%")
        avg_ms = (total_latency_sec / total) * 1000
        qps = total / total_latency_sec
        print(f"Total Inference Time: {total_latency_sec:.4f}s")
        print(f"Average Latency per Query: {avg_ms:.4f} ms")
        print(f"Throughput (QPS): {qps:.0f} queries/sec")

        print("\n--- Accuracy by Tag ---")
        for tag, stats in stats_by_tag.items():
            if stats["total"] > 0:
                acc = (stats["hits_at_1"] / stats["total"]) * 100
                print(f"  {tag}: {acc:.2f}% ({stats['hits_at_1']}/{stats['total']})")

if __name__ == "__main__":
    run_benchmark()
