import sqlite3
import spacy
from spacy.tokens import DocBin
import os
import contextlib

from benchmarks.noise_injector import inject_noise

def generate_datasets(db_path, train_out, dev_out, txt_out, limit=1000):
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
                
                query = street_noisy
                if neigh:
                    query += " " + neigh
                    
                f_txt.write(query + "\n")
                    
                doc = nlp.make_doc(query)
                ents = []
                
                start_idx = 0
                end_idx = len(street_noisy)
                span = doc.char_span(start_idx, end_idx, label="STREET")
                if span is None:
                    continue
                ents.append(span)
                
                if neigh:
                    n_idx = end_idx + 1
                    span_n = doc.char_span(n_idx, n_idx + len(neigh), label="NEIGH")
                    if span_n is None:
                        continue
                    ents.append(span_n)
                
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
        limit=50000
    )
