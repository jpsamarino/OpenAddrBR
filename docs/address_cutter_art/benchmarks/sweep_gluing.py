import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from openaddrbr.core._address_cutter import AddressCutter
from benchmarks.benchmark_address_cutter import JSON_STATS, SGEODB, PROB_TOKEN_GLUING, PROB_TYPING_STREET, PROB_TYPING_NUMBER, PROB_INJECT_NUMBER_IN_NEIGHBORHOOD
from benchmarks.noise_injector import inject_noise
import sqlite3
import random

def run_sweep():
    # Load rows once
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT 20000"
    )
    rows = cursor.fetchall()
    
    thresholds = [None, 1, 2, 3, 4]
    
    for t in thresholds:
        cutter = AddressCutter(JSON_STATS, gluing_threshold=t)
        
        hits_at_1 = 0
        hits_gluing_at_1 = 0
        total_gluing = 0
        total = 0
        
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
            
            cuts = cutter.cut(query)
            total += 1
            if "token_gluing" in tags:
                total_gluing += 1
            
            correct_position = -1
            for idx, hypothesis in enumerate(cuts):
                if hypothesis.street_part == expected_street:
                    correct_position = idx
                    break
                    
            if correct_position != -1:
                rank = correct_position + 1
                if rank == 1:
                    hits_at_1 += 1
                    if "token_gluing" in tags:
                        hits_gluing_at_1 += 1
                        
        acc = (hits_at_1 / total) * 100
        gluing_acc = (hits_gluing_at_1 / total_gluing) * 100 if total_gluing > 0 else 0
        print(f"Threshold: {str(t):4} | Global Acc: {acc:.2f}% | Gluing Acc: {gluing_acc:.2f}%")

if __name__ == "__main__":
    run_sweep()
