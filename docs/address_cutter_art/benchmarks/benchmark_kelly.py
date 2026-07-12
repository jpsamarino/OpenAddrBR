import os
import sys
import time
import math
import random
import sqlite3

# Add root to pythonpath
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from openaddrbr.core._address_cutter import AddressCutter
from openaddrbr.utils._text import normalize_text
from openaddrbr.core.models._models import CutHypothesis, Role, Pos

class AddressCutterKelly(AddressCutter):
    def _score_street(self, tokens: list[str], start: int, end: int) -> float:
        L = end - start
        if L == 0:
            return 0.0

        score = 0.0
        for i in range(start, end):
            token = tokens[i]
            pos = self.token_position(i - start, L)

            ts = self.stats.get((token, Role.STREET, pos))
            weight = self.weights.get(token, 0.0)

            if not ts:
                score -= 15.0
                continue

            llr = ts.llr
            mean = ts.mean
            std = ts.std
            gaussian_penalty = -((L - mean) ** 2) / (2 * (std ** 2))

            if llr < 0:
                kelly_fraction = 0.15 + 0.85 * math.exp(llr / 2.0)
                token_score = (llr * weight * kelly_fraction) + gaussian_penalty
            else:
                token_score = (llr * weight) + gaussian_penalty

            if pos == Pos.END and L > 2 and token.isdigit():
                token_score -= 20.0

            score += token_score

        return score

def run_kelly_benchmark():
    db_path = "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db"
    json_path = "data/address_stats.json"
    
    print("Loading Kelly Address Cutter...")
    cutter = AddressCutterKelly(json_path)
    
    print("Connecting to database...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT street_normalized, neighborhood_normalized 
        FROM address 
        WHERE street_normalized IS NOT NULL 
        ORDER BY RANDOM() LIMIT 100000
    """)
    samples = cursor.fetchall()
    conn.close()
    
    print("Running Kelly Benchmark on 100,000 queries...")
    
    hits_top1 = 0
    hits_top3 = 0
    mrr_sum = 0.0
    total_time = 0.0
    
    for street, neighborhood in samples:
        street_clean = normalize_text(street)
        if not street_clean: continue
        neighborhood = normalize_text(neighborhood) if neighborhood else ""
        
        rand_val = random.random()
        if rand_val < 0.33:
            street_tokens = street_clean.split()
            if not street_tokens: continue
            partial_street = " ".join(street_tokens[:-1])
            last_token = street_tokens[-1]
            cut_idx = random.randint(1, len(last_token))
            partial_last = last_token[:cut_idx]
            expected_street = f"{partial_street} {partial_last}" if partial_street else partial_last
            query = expected_street
        elif rand_val < 0.66:
            house_number = str(random.randint(1, 9999))
            cut_idx = random.randint(1, len(house_number))
            partial_number = house_number[:cut_idx]
            query = f"{street_clean} {partial_number}"
            expected_street = street_clean
        else:
            has_number = random.random() < 0.8
            house_number = str(random.randint(1, 9999)) if has_number else ""
            neigh_tokens = neighborhood.strip().split()
            if not neigh_tokens:
                query = f"{street_clean} {house_number}" if has_number else street_clean
                expected_street = street_clean
            else:
                partial_neigh = " ".join(neigh_tokens[:-1])
                last_token = neigh_tokens[-1]
                cut_idx = random.randint(1, len(last_token))
                partial_last = last_token[:cut_idx]
                partial_neigh = f"{partial_neigh} {partial_last}" if partial_neigh else partial_last
                query = f"{street_clean} {house_number} {partial_neigh}" if has_number else f"{street_clean} {partial_neigh}"
                expected_street = street_clean
                
        t0 = time.perf_counter()
        cuts = cutter.cut(query)
        t1 = time.perf_counter()
        total_time += (t1 - t0)
        
        rank = -1
        for i, cut in enumerate(cuts):
            if cut.street_part == expected_street:
                rank = i + 1
                break
                
        if rank == 1: hits_top1 += 1
        if 1 <= rank <= 3: hits_top3 += 1
        if rank > 0: mrr_sum += 1.0 / rank

    print(f"\n--- Kelly Benchmark Results ---")
    print(f"Top 1 Accuracy: {(hits_top1/len(samples))*100:.2f}%")
    print(f"Top 3 Accuracy: {(hits_top3/len(samples))*100:.2f}%")
    print(f"Mean Reciprocal Rank (MRR): {mrr_sum/len(samples):.4f}")

if __name__ == '__main__':
    run_kelly_benchmark()
