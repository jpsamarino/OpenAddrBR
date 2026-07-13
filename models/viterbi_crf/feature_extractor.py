import os
import marisa_trie

# Carregamento Lazy
_STREET_TRIE = None
_NEIGH_TRIE = None

# Dicionário de normalização reversa para expandir abreviações na consulta Trie
REVERSE_ABBREVIATIONS = {
    "AV": "AVENIDA", "AV.": "AVENIDA",
    "DR": "DOUTOR", "DR.": "DOUTOR",
    "PROF": "PROFESSOR",
    "PRES": "PRESIDENTE",
    "S": "SÃO", "S.": "SÃO",
    "STO": "SANTO",
    "STA": "SANTA",
    "GEN": "GENERAL",
    "CEL": "CORONEL",
    "CAP": "CAPITAO",
    "SGT": "SARGENTO",
    "N": "NOSSA", "N.": "NOSSA",
    "NSA": "NOSSA",
    "SRA": "SENHORA", "SRA.": "SENHORA",
    "R": "RUA", "R.": "RUA",
    "TRAV": "TRAVESSA", "TRAV.": "TRAVESSA",
}

def get_tries():
    global _STREET_TRIE, _NEIGH_TRIE
    if _STREET_TRIE is None:
        p_street = os.path.join(os.path.dirname(__file__), "streets.trie")
        p_neigh = os.path.join(os.path.dirname(__file__), "neigh.trie")
        
        _STREET_TRIE = marisa_trie.Trie()
        _NEIGH_TRIE = marisa_trie.Trie()
        
        if os.path.exists(p_street):
            _STREET_TRIE.load(p_street)
        if os.path.exists(p_neigh):
            _NEIGH_TRIE.load(p_neigh)
    return _STREET_TRIE, _NEIGH_TRIE

def is_prefix_in_trie(phrase, trie):
    if not trie:
        return False
    # Normalizar abreviações na frase antes da consulta
    words = phrase.upper().split()
    normalized_words = [REVERSE_ABBREVIATIONS.get(w, w) for w in words]
    normalized_phrase = " ".join(normalized_words)
    
    return trie.has_keys_with_prefix(normalized_phrase)

def word2features(sent, i):
    word = sent[i]
    st_trie, ne_trie = get_tries()
    
    phrase_so_far = " ".join(sent[:i+1])
    
    features = {
        'bias': 1.0,
        'word.lower()': word.lower(),
        'word[-3:]': word[-3:] if len(word) >= 3 else word,
        'word[-2:]': word[-2:] if len(word) >= 2 else word,
        'word[:3]': word[:3] if len(word) >= 3 else word,
        'word.isupper()': word.isupper(),
        'word.istitle()': word.istitle(),
        'word.isdigit()': word.isdigit(),
        'word.length': len(word),
    # Libpostal Magic: Consulta Trie considerando a frase inteira
    'phrase_in_street_trie': is_prefix_in_trie(phrase_so_far, st_trie),
    'phrase_in_neigh_trie': is_prefix_in_trie(phrase_so_far, ne_trie),
    }
    
    # Extrair todos os character n-grams (3-grams e 4-grams) do token para tolerar Typos
    for n in [3, 4]:
        for j in range(len(word) - n + 1):
            features[f'char_{n}gram_{j}'] = word[j:j+n].lower()
    if i > 0:
        word1 = sent[i-1]
        features.update({
            '-1:word.lower()': word1.lower(),
            '-1:word.isupper()': word1.isupper(),
            '-1:word.isdigit()': word1.isdigit(),
        })
    else:
        features['BOS'] = True # Begin of sequence

    if i < len(sent)-1:
        word1 = sent[i+1]
        features.update({
            '+1:word.lower()': word1.lower(),
            '+1:word.isupper()': word1.isupper(),
            '+1:word.isdigit()': word1.isdigit(),
        })
    else:
        features['EOS'] = True # End of sequence

    return features

def sent2features(sent):
    return [word2features(sent, i) for i in range(len(sent))]

def sent2labels(sent):
    # assumindo sent = lista de tuples (word, label) ou jsonl dict
    return [label for _, label in sent]
