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

from models.viterbi_crf.predictor import ViterbiCRF

def run_benchmark(model_path="models/crf_poc/model-best"):
    print(f"Loading CRF (spaCy) model from {model_path}...")
    try:
        nlp = spacy.load(model_path)
    except OSError:
        print("SpaCy Model not found, skipping SpaCy.")
        nlp = None
        
    print("Loading Viterbi CRF...")
    try:
        viterbi = ViterbiCRF()
    except Exception as e:
        print(f"Erro no Viterbi: {e}")
        viterbi = None

    if not os.path.exists(SGEODB):
        print(f"Error: Database not found at {SGEODB}")
        sys.exit(1)

    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT {LIMIT_SAMPLES}")
    rows = cursor.fetchall()

    hits_spacy = 0
    hits_viterbi = 0
    total = 0
    stats_spacy = defaultdict(lambda: {"total": 0, "hits": 0})
    stats_viterbi = defaultdict(lambda: {"total": 0, "hits": 0})
    latency_spacy = 0.0
    latency_viterbi = 0.0

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

        if nlp:
            t0 = time.perf_counter()
            doc = nlp(query)
            t1 = time.perf_counter()
            latency_spacy += t1 - t0

            pred_street = ""
            for ent in doc.ents:
                if ent.label_ == "STREET":
                    pred_street = ent.text
                    break
            
            if pred_street == expected_street or expected_street in pred_street:
                hits_spacy += 1
                for tag in tags:
                    stats_spacy[tag]["hits"] += 1
                    
        if viterbi:
            t0 = time.perf_counter()
            res = viterbi.parse(query)
            t1 = time.perf_counter()
            latency_viterbi += t1 - t0
            
            pred_viterbi = res.get("STREET", "")
            if pred_viterbi == expected_street or expected_street in pred_viterbi:
                hits_viterbi += 1
                for tag in tags:
                    stats_viterbi[tag]["hits"] += 1

        total += 1
        for tag in tags:
            stats_spacy[tag]["total"] += 1
            stats_viterbi[tag]["total"] += 1

    print(f"\n--- Benchmark Results ({total} queries) ---")
    if total > 0:
        if nlp:
            print("\n*** SpaCy CRF ***")
            print(f"Top 1 Accuracy: {(hits_spacy / total) * 100:.2f}%")
            print(f"Throughput (QPS): {total / latency_spacy:.0f} queries/sec")
            for tag, stats in stats_spacy.items():
                if stats["total"] > 0:
                    acc = (stats["hits"] / stats["total"]) * 100
                    print(f"  {tag}: {acc:.2f}%")
                    
        if viterbi:
            print("\n*** Viterbi CRF + Trie ***")
            print(f"Top 1 Accuracy: {(hits_viterbi / total) * 100:.2f}%")
            print(f"Throughput (QPS): {total / latency_viterbi:.0f} queries/sec")
            for tag, stats in stats_viterbi.items():
                if stats["total"] > 0:
                    acc = (stats["hits"] / stats["total"]) * 100
                    print(f"  {tag}: {acc:.2f}%")

if __name__ == "__main__":
    run_benchmark()
