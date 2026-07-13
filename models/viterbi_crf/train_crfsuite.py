import pycrfsuite
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from viterbi_crf.feature_extractor import sent2features

def train_model(train_path, dev_path, out_path):
    trainer = pycrfsuite.Trainer(verbose=True)
    
    print(f"Carregando dados de treino de: {train_path}")
    with open(train_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i > 0 and i % 100000 == 0:
                print(f"Lidos {i} registros...")
            item = json.loads(line)
            xseq = sent2features(item["tokens"])
            yseq = item["labels"]
            trainer.append(xseq, yseq)
            
    # Dev set can be used as holdout for evaluation during training, but pycrfsuite 
    # handles this via cross-validation or we can just train on train and test later.
    
    print("Configurando CRF (L-BFGS com Regularização L1/L2)...")
    trainer.set_params({
        'c1': 0.1,   # coeficiente para regularização L1 (promove sparsity)
        'c2': 0.05,  # coeficiente para regularização L2
        'max_iterations': 150,
        'feature.possible_transitions': True,
        'feature.minfreq': 2
    })
    
    print("Iniciando treinamento com Viterbi Inference (C++ backend)...")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    trainer.train(out_path)
    
    print(f"Treinamento concluído! Modelo salvo em: {out_path}")

if __name__ == "__main__":
    train_model(
        "data/train_viterbi.jsonl",
        "data/dev_viterbi.jsonl",
        "models/viterbi_crf/model.crfsuite"
    )
