import sqlite3
import spacy
from spacy.tokens import DocBin
import os
import random
import multiprocessing
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from benchmarks.noise_injector import inject_noise

def process_chunk(rows):
    nlp = spacy.blank("pt")
    docs = []
    
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
            
        # Simular corte (autocomplete) no último elemento que vai ser digitado
        is_cut = random.random() < 0.3 # 30% de chance de ser uma string incompleta
        
        query = street_noisy
        
        number_str = ""
        if has_number:
            number_str = str(random.randint(1, 9999))
            
        if is_cut:
            if has_neigh and neigh:
                # Corta o bairro pela metade
                cut_idx = random.randint(1, len(neigh))
                neigh = neigh[:cut_idx]
            elif has_number:
                # Corta o numero
                cut_idx = random.randint(1, max(2, len(number_str)))
                number_str = number_str[:cut_idx]
            else:
                # Corta a rua
                lower_bound = max(1, len(street_noisy) // 2)
                upper_bound = max(lower_bound, len(street_noisy))
                cut_idx = random.randint(lower_bound, upper_bound)
                street_noisy = street_noisy[:cut_idx]
                query = street_noisy
                
        if has_number:
            query += " " + number_str
            
        if has_neigh and neigh:
            query += " " + neigh
            
        doc = nlp.make_doc(query)
        ents = []
        
        s_end = len(street_noisy)
        span = doc.char_span(0, s_end, label="STREET")
        if span is None:
            continue
        ents.append(span)
        
        curr_idx = s_end
        skip = False
        if has_number:
            curr_idx += 1
            span_num = doc.char_span(curr_idx, curr_idx + len(number_str), label="NUMBER")
            if span_num is None:
                skip = True
            else:
                ents.append(span_num)
            curr_idx += len(number_str)
            
        if skip:
            continue
            
        if has_neigh and neigh:
            curr_idx += 1
            span_ne = doc.char_span(curr_idx, curr_idx + len(neigh), label="NEIGH")
            if span_ne is None:
                skip = True
            else:
                ents.append(span_ne)
                
        if skip:
            continue
            
        try:
            doc.ents = ents
            docs.append(doc)
        except ValueError:
            pass
            
    dbin = DocBin(docs=docs)
    return dbin.to_bytes()

def generate_datasets(db_path, train_out, dev_out, txt_out, limit=2000000):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    for out_path in [train_out, dev_out, txt_out]:
        dir_name = os.path.dirname(out_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    print(f"Buscando {limit} endereços do SQLite...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address WHERE street_normalized IS NOT NULL AND street_normalized != '' ORDER BY RANDOM() LIMIT {limit}")
    all_rows = cursor.fetchall()
    conn.close()
    
    print("Gerando corpus de texto...")
    with open(txt_out, "w", encoding="utf-8") as f_txt:
        for row in all_rows:
            f_txt.write(row[0].strip() + "\n")
            
    num_cores = multiprocessing.cpu_count()
    if len(all_rows) == 0:
        print("Nenhum dado encontrado.")
        return
        
    chunk_size = math.ceil(len(all_rows) / (num_cores * 4))
    if chunk_size == 0: chunk_size = 1
    chunks = [all_rows[i:i + chunk_size] for i in range(0, len(all_rows), chunk_size)]
    
    print(f"Iniciando multiprocessing com {num_cores} núcleos. Total de {len(chunks)} lotes...")
    
    final_docs = []
    nlp = spacy.blank("pt")
    
    with multiprocessing.Pool(num_cores) as pool:
        for i, docbin_bytes in enumerate(pool.imap_unordered(process_chunk, chunks)):
            dbin = DocBin().from_bytes(docbin_bytes)
            for doc in dbin.get_docs(nlp.vocab):
                final_docs.append(doc)
            print(f"Progresso: Lote {i+1}/{len(chunks)} concluído. ({len(final_docs)} docs anotados)")
            
    print("Dividindo em Train e Dev...")
    split_idx = int(len(final_docs) * 0.8)
    train_docs = final_docs[:split_idx]
    dev_docs = final_docs[split_idx:]

    print(f"Salvando {len(train_docs)} em train e {len(dev_docs)} em dev...")
    train_bin = DocBin(docs=train_docs)
    train_bin.to_disk(train_out)

    dev_bin = DocBin(docs=dev_docs)
    dev_bin.to_disk(dev_out)
    print("Concluído!")

if __name__ == "__main__":
    db_path = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
    generate_datasets(
        db_path,
        "data/train_crf.spacy",
        "data/dev_crf.spacy",
        "data/corpus_fasttext_crf.txt",
        limit=2000000
    )
