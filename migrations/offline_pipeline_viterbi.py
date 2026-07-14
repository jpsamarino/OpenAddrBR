import sqlite3
import os
import random
import multiprocessing
import sys
import math
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from benchmarks.noise_injector import inject_noise

def process_chunk(rows):
    dataset = []
    
    for row in rows:
        street = row[0].strip()
        neigh = row[1].strip() if row[1] else ""
        
        street_noisy, _ = inject_noise(street)
        if not street_noisy:
            continue
            
        query_type = random.random()
        has_number = False
        has_neigh = False
        
        if query_type < 0.2:
            pass
        elif query_type < 0.5:
            has_number = True
        elif query_type < 0.9:
            has_number = True
            has_neigh = True
        else:
            has_neigh = True
            
        is_cut = random.random() < 0.3 # 30% chance de autocomplete cut
        
        number_str = ""
        if has_number:
            number_str = str(random.randint(1, 9999))
            
        if is_cut:
            if has_neigh and neigh:
                cut_idx = random.randint(1, len(neigh))
                neigh = neigh[:cut_idx]
            elif has_number:
                cut_idx = random.randint(1, max(2, len(number_str)))
                number_str = number_str[:cut_idx]
            else:
                lower_bound = max(1, len(street_noisy) // 2)
                upper_bound = max(lower_bound, len(street_noisy))
                cut_idx = random.randint(lower_bound, upper_bound)
                street_noisy = street_noisy[:cut_idx]
                
        # Gerar tokens e BIO tags diretamente
        tokens = []
        labels = []
        
        st_tokens = street_noisy.split()
        for i, t in enumerate(st_tokens):
            tokens.append(t)
            labels.append("B-STREET" if i == 0 else "I-STREET")
            
        if has_number:
            tokens.append(number_str)
            labels.append("B-NUMBER")
            
        if has_neigh and neigh:
            ne_tokens = neigh.split()
            for i, t in enumerate(ne_tokens):
                tokens.append(t)
                labels.append("B-NEIGH" if i == 0 else "I-NEIGH")
                
        if tokens:
            dataset.append({"tokens": tokens, "labels": labels})
            
    return dataset

def generate_datasets(db_path, train_out, dev_out, limit=2000000):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    for out_path in [train_out, dev_out]:
        dir_name = os.path.dirname(out_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    print(f"Buscando {limit} endereços do SQLite...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address WHERE street_normalized IS NOT NULL AND street_normalized != '' ORDER BY RANDOM() LIMIT {limit}")
    all_rows = cursor.fetchall()
    conn.close()
    
    num_cores = multiprocessing.cpu_count()
    if len(all_rows) == 0:
        return
        
    chunk_size = math.ceil(len(all_rows) / (num_cores * 4))
    if chunk_size == 0: chunk_size = 1
    chunks = [all_rows[i:i + chunk_size] for i in range(0, len(all_rows), chunk_size)]
    
    print(f"Iniciando multiprocessing com {num_cores} núcleos. Total de {len(chunks)} lotes...")
    
    final_data = []
    
    with multiprocessing.Pool(num_cores) as pool:
        for i, result in enumerate(pool.imap_unordered(process_chunk, chunks)):
            final_data.extend(result)
            print(f"Progresso: Lote {i+1}/{len(chunks)} concluído. ({len(final_data)} docs)")
            
    print("Dividindo em Train e Dev...")
    split_idx = int(len(final_data) * 0.8)
    train_data = final_data[:split_idx]
    dev_data = final_data[split_idx:]

    print(f"Salvando JSONL...")
    with open(train_out, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(dev_out, "w", encoding="utf-8") as f:
        for item in dev_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    print("Concluído!")

if __name__ == "__main__":
    db_path = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
    generate_datasets(
        db_path,
        "data/train_viterbi.jsonl",
        "data/dev_viterbi.jsonl",
        limit=2000000
    )
