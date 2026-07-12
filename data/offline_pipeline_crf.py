import sqlite3
import spacy
from spacy.tokens import DocBin
import os
import random
import contextlib

from benchmarks.noise_injector import inject_noise

def generate_datasets(db_path, train_out, dev_out, txt_out, limit=200000):
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}")

    for out_path in [train_out, dev_out, txt_out]:
        dir_name = os.path.dirname(out_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    nlp = spacy.blank("pt")
    
    with contextlib.closing(sqlite3.connect(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address WHERE street_normalized IS NOT NULL AND street_normalized != '' ORDER BY RANDOM() LIMIT {limit}")
        
        docs = []
        
        with open(txt_out, "w", encoding="utf-8") as f_txt:
            for row in cursor:
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
                
                query = street_noisy
                
                number_str = ""
                if has_number:
                    number_str = str(random.randint(1, 9999))
                    query += " " + number_str
                    
                if has_neigh and neigh:
                    query += " " + neigh
                    
                f_txt.write(query + "\n")
                    
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

        split_idx = int(len(docs) * 0.8)
        train_docs = docs[:split_idx]
        dev_docs = docs[split_idx:]

        train_bin = DocBin()
        for d in train_docs:
            train_bin.add(d)
        train_bin.to_disk(train_out)

        dev_bin = DocBin()
        for d in dev_docs:
            dev_bin.add(d)
        dev_bin.to_disk(dev_out)

if __name__ == "__main__":
    db_path = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")
    generate_datasets(
        db_path,
        "data/train_crf.spacy",
        "data/dev_crf.spacy",
        "data/corpus_fasttext_crf.txt",
        limit=200000
    )
