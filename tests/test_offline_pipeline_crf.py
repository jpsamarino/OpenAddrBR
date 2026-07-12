import os
import pytest
from data.offline_pipeline_crf import generate_datasets

def test_generate_datasets(tmp_path):
    db_path = tmp_path / "dummy.db"
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE address (street_normalized TEXT, neighborhood_normalized TEXT, city_code TEXT)")
    conn.execute("INSERT INTO address VALUES ('RUA JOSE COSTA', 'CENTRO', '123')")
    conn.commit()
    conn.close()
    
    train_out = tmp_path / "train_crf.spacy"
    txt_out = tmp_path / "corpus_crf.txt"
    
    generate_datasets(str(db_path), str(train_out), str(txt_out), limit=1)
    assert train_out.exists()
    assert txt_out.exists()
