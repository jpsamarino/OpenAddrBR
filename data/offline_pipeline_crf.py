import sqlite3
import spacy
from spacy.tokens import DocBin
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from benchmarks.noise_injector import inject_noise

def generate_datasets(db_path, spacy_out, txt_out, limit=1000):
    nlp = spacy.blank("pt")
    doc_bin = DocBin()
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(f"SELECT street_normalized, neighborhood_normalized FROM address WHERE street_normalized IS NOT NULL AND street_normalized != '' LIMIT {limit}")
    
    with open(txt_out, "w", encoding="utf-8") as f_txt:
        for row in cursor:
            street = row[0].strip()
            neigh = row[1].strip() if row[1] else ""
            
            f_txt.write(street + "\n")
            if neigh:
                f_txt.write(neigh + "\n")
            
            street_noisy, _ = inject_noise(street)
            if not street_noisy:
                continue
            
            query = street_noisy
            if neigh:
                query += " " + neigh
                
            doc = nlp.make_doc(query)
            ents = []
            
            start_idx = query.find(street_noisy)
            if start_idx != -1:
                span = doc.char_span(start_idx, start_idx + len(street_noisy), label="STREET")
                if span:
                    ents.append(span)
            
            if neigh:
                n_idx = query.find(neigh)
                if n_idx != -1:
                    span_n = doc.char_span(n_idx, n_idx + len(neigh), label="NEIGH")
                    if span_n:
                        ents.append(span_n)
            
            try:
                doc.ents = ents
                doc_bin.add(doc)
            except ValueError:
                pass

    doc_bin.to_disk(spacy_out)
    conn.close()

if __name__ == "__main__":
    generate_datasets(
        "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db",
        "data/train_crf.spacy",
        "data/corpus_fasttext_crf.txt",
        limit=50000
    )
