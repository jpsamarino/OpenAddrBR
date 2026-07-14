import os
import pytest
import spacy
from spacy.tokens import DocBin
from data.offline_pipeline_crf import generate_datasets

from unittest.mock import patch

@patch("data.offline_pipeline_crf.inject_noise")
@patch("random.random")
@patch("random.randint")
def test_generate_datasets(mock_randint, mock_random, mock_inject_noise, tmp_path):
    mock_inject_noise.side_effect = lambda x: (x, ["mock"])
    mock_random.return_value = 0.6  # [STREET] [NUMBER] [NEIGHBORHOOD]
    mock_randint.return_value = 123
    db_path = tmp_path / "dummy.db"
    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE address (street_normalized TEXT, neighborhood_normalized TEXT, city_code TEXT)")
    conn.execute("INSERT INTO address VALUES ('RUA UM', 'BAIRRO UM', '123')")
    conn.execute("INSERT INTO address VALUES ('RUA DOIS', 'BAIRRO DOIS', '123')")
    conn.execute("INSERT INTO address VALUES ('RUA TRES', 'BAIRRO TRES', '123')")
    conn.execute("INSERT INTO address VALUES ('RUA QUATRO', 'BAIRRO QUATRO', '123')")
    conn.execute("INSERT INTO address VALUES ('RUA CINCO', 'BAIRRO CINCO', '123')")
    conn.commit()
    conn.close()
    
    train_out = tmp_path / "train_crf.spacy"
    dev_out = tmp_path / "dev_crf.spacy"
    txt_out = tmp_path / "corpus_crf.txt"
    
    generate_datasets(str(db_path), str(train_out), str(dev_out), str(txt_out), limit=5)
    
    assert train_out.exists()
    assert dev_out.exists()
    assert txt_out.exists()
    
    nlp = spacy.blank("pt")
    
    train_bin = DocBin().from_disk(train_out)
    train_docs = list(train_bin.get_docs(nlp.vocab))
    
    dev_bin = DocBin().from_disk(dev_out)
    dev_docs = list(dev_bin.get_docs(nlp.vocab))
    
    # 80% of 5 is 4
    assert len(train_docs) == 4
    assert len(dev_docs) == 1
    
    for doc in train_docs + dev_docs:
        ents = {ent.label_: ent.text for ent in doc.ents}
        assert "STREET" in ents  # Toda query obrigatoriamente tem street
        for label in ents:
            assert label in {"STREET", "NUMBER", "NEIGH"}
        
    with open(txt_out, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        
    assert len(lines) == 5
