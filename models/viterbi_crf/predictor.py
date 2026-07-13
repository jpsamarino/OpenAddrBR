import os
import pycrfsuite
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from viterbi_crf.feature_extractor import sent2features

import re

TOKEN_RE = re.compile(r'([A-Za-zÀ-ÿ\.\-]+|\d+)')

class ViterbiCRF:
    def __init__(self, model_path=None):
        if model_path is None:
            model_path = os.path.join(os.path.dirname(__file__), "model.crfsuite")
        
        self.tagger = pycrfsuite.Tagger()
        self.tagger.open(model_path)
        
    def parse(self, text):
        """
        Recebe uma string, aplica a feature extraction,
        e retorna uma lista de dicionários com os campos extraídos.
        """
        # Tokenização inteligente que separa letras e números (evita token gluing)
        tokens = TOKEN_RE.findall(text.upper())
        if not tokens:
            return {}
            
        xseq = sent2features(tokens)
        yseq = self.tagger.tag(xseq)
        
        # Agrupar B- e I- tags
        result = {}
        current_label = None
        current_tokens = []
        
        for token, label in zip(tokens, yseq):
            base_label = label.replace("B-", "").replace("I-", "") if label != "O" else "O"
            
            if label.startswith("B-"):
                if current_label:
                    result[current_label] = " ".join(current_tokens)
                current_label = base_label
                current_tokens = [token]
            elif label.startswith("I-") and current_label == base_label:
                current_tokens.append(token)
            else:
                if current_label:
                    result[current_label] = " ".join(current_tokens)
                    current_label = None
                    current_tokens = []
        
        if current_label:
            result[current_label] = " ".join(current_tokens)
            
        return result
