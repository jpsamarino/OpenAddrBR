import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from openaddrbr.core._address_cutter import AddressCutter
from benchmarks.benchmark_address_cutter import JSON_STATS, SGEODB, PROB_TOKEN_GLUING, PROB_TYPING_STREET, PROB_TYPING_NUMBER, PROB_INJECT_NUMBER_IN_NEIGHBORHOOD
from benchmarks.noise_injector import inject_noise
import sqlite3
import random

def run_kelly_sweep():
    conn = sqlite3.connect(SGEODB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT street_normalized, neighborhood_normalized FROM address ORDER BY RANDOM() LIMIT 50000"
    )
    rows = cursor.fetchall()
    
    # Kelly configurations to test
    # Format: (use_kelly, kelly_min, kelly_decay)
    configs = [
        (False, 0.0, 0.0), # Baseline (llr_floor = -3.0)
        (True, 0.15, 2.0), # Colleague's original
        (True, 0.30, 2.0), # Higher floor
        (True, 0.05, 1.0), # Aggressive decay
        (True, 0.50, 4.0), # Very soft decay
    ]
    
    for use_kelly, k_min, k_decay in configs:
        cutter = AddressCutter(
            JSON_STATS, 
            use_kelly=use_kelly, 
            kelly_min=k_min, 
            kelly_decay=k_decay
        )
        
        hits_at_1 = 0
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
            
            correct_position = -1
            for idx, hypothesis in enumerate(cuts):
                if hypothesis.street_part == expected_street:
                    correct_position = idx
                    break
                    
            if correct_position == 0:
                hits_at_1 += 1
                        
        acc = (hits_at_1 / total) * 100
        print(f"Kelly: {str(use_kelly):5} | Min: {k_min:4} | Decay: {k_decay:4} => Global Acc: {acc:.2f}%")

if __name__ == "__main__":
    run_kelly_sweep()
