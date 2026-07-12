import pytest
from scripts.train_crf_poc import train_fasttext

def test_train_fasttext(tmp_path):
    corpus_file = tmp_path / "corpus.txt"
    corpus_file.write_text("RUA JOSE COSTA\nAVENIDA PAULISTA\n", encoding="utf-8")
    out_model = tmp_path / "ft.model"
    train_fasttext(str(corpus_file), str(out_model), epochs=1)
    assert out_model.exists()
