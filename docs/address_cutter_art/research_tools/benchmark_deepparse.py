import os
import random
import sqlite3
import sys
import time
from collections import defaultdict

try:
    from deepparse.parser import AddressParser
except ImportError:
    print("ERRO: O pacote 'deepparse' não está instalado.")
    sys.exit(1)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from benchmarks.noise_injector import inject_noise

SGEODB = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
LIMIT_SAMPLES = 100000

PROB_TYPING_STREET = 0.33
PROB_TYPING_NUMBER = 0.66

def run_benchmark():
    print("Iniciando Benchmark do Deepparse...")
    
    if not os.path.exists(SGEODB):
        print(f"Banco não encontrado em {SGEODB}")
        return

    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT {LIMIT_SAMPLES}")
    rows = cursor.fetchall()

    hits_at_1 = 0
    total = 0
    stats_by_tag = defaultdict(lambda: {"total": 0, "hits_at_1": 0})
    total_latency_sec = 0.0

    print("Carregando modelo BPEmb...")
    # fallback to CPU if CUDA is not available
    import torch
    device = 0 if torch.cuda.is_available() else "cpu"
    parser = AddressParser(model_type="bpemb", device=device)

    # Pre-build queries
    queries = []
    expected_streets = []
    all_tags = []

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

        queries.append(query)
        expected_streets.append(expected_street)
        all_tags.append(tags)

    print(f"Processando {len(queries)} queries...")
    t0 = time.perf_counter()
    
    # Deepparse supports batch parsing!
    BATCH_SIZE = 512
    parsed_results = []
    
    # Actually, we can just pass the whole list to parser() and it batches internally,
    # but let's do it in chunks to avoid memory explosion
    for i in range(0, len(queries), BATCH_SIZE):
        batch = queries[i:i+BATCH_SIZE]
        parsed_batch = parser(batch)
        if isinstance(parsed_batch, list):
            parsed_results.extend(parsed_batch)
        else:
            parsed_results.append(parsed_batch)
            
    t1 = time.perf_counter()
    total_latency_sec = t1 - t0
    total = len(queries)

    # Evaluate
    for i, parsed in enumerate(parsed_results):
        expected_street = expected_streets[i]
        tags = all_tags[i]
        
        # Deepparse components: StreetName, StreetNumber, Municipality, etc
        street_val = parsed.to_dict().get("StreetName")
        pred_street = (street_val if street_val else "").upper()
        
        # Fair comparison
        if pred_street == expected_street or expected_street in pred_street or pred_street in expected_street:
            hits_at_1 += 1
            for tag in tags:
                stats_by_tag[tag]["hits_at_1"] += 1
                
        for tag in tags:
            stats_by_tag[tag]["total"] += 1

    print(f"\n--- Deepparse Benchmark Results ({total} queries) ---")
    if total > 0:
        print(f"Top 1 Accuracy (StreetName mapping): {(hits_at_1 / total) * 100:.2f}%")
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
