import os
import subprocess
from gensim.models import FastText

def train_fasttext(corpus_path, output_path, epochs=5):
    print("Treinando FastText (Gensim)...")
    class MyCorpus:
        def __iter__(self):
            for line in open(corpus_path, encoding="utf-8"):
                yield line.strip().split()
                
    sentences = MyCorpus()
    model = FastText(sentences, vector_size=50, window=3, min_count=1, epochs=epochs)
    model.save(output_path)
    
    w2v_path = output_path + ".txt"
    model.wv.save_word2vec_format(w2v_path)
    return w2v_path

def init_spacy_config():
    os.makedirs("models/crf_poc", exist_ok=True)
    subprocess.run(["python", "-m", "spacy", "init", "config", "models/crf_poc/config_crf.cfg", "--lang", "pt", "--pipeline", "ner", "--optimize", "efficiency", "--force"], check=True)

if __name__ == "__main__":
    w2v_path = train_fasttext("data/corpus_fasttext_crf.txt", "data/fasttext_crf.model")
    init_spacy_config()
    subprocess.run(["python", "-m", "spacy", "init", "vectors", "pt", w2v_path, "data/spacy_vectors_crf"], check=True)
