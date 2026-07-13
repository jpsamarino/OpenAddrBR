import os
import sys
import sqlite3
import spacy

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from models.viterbi_crf.predictor import ViterbiCRF

try:
    from openaddrbr.core._address_cutter import AddressCutter
    cutter_original = AddressCutter(json_path="data/address_stats.json")
except ImportError:
    cutter_original = None

try:
    nlp_crf = spacy.load("models/crf_poc/model-best")
except Exception:
    nlp_crf = None
    
try:
    cutter_viterbi = ViterbiCRF()
except Exception as e:
    print(f"Erro ao carregar Viterbi: {e}")
    cutter_viterbi = None

# 3. Load Libpostal (if available, otherwise we test it in Docker)
try:
    from postal.parser import parse_address
except ImportError:
    parse_address = None

SGEODB = os.environ.get("SGEOBR_DB_PATH", "D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db")

conn = sqlite3.connect(SGEODB)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT street_normalized FROM address WHERE street_normalized IS NOT NULL ORDER BY RANDOM() LIMIT 2000")
rows = cursor.fetchall()

def chop_last_word(street):
    tokens = street.split()
    if len(tokens) < 2:
        return None
    last = tokens[-1]
    if len(last) < 4:
        return None
    tokens[-1] = last[:len(last)//2]
    return " ".join(tokens)

test_cases = []
for row in rows:
    street = row["street_normalized"].strip()
    chopped = chop_last_word(street)
    if chopped:
        test_cases.append((chopped, street))
        if len(test_cases) == 500:
            break

print(f"Testando {len(test_cases)} casos de Autocomplete (ex: 'RUA JOSE COSTA' -> 'RUA JOSE CO')\n")

# Test Original
acertos_original = 0
acertos_spacy = 0
acertos_viterbi = 0
    
for case in test_cases:
    # Original
    if cutter_original:
        hyps = cutter_original.cut(case[0])
        if hyps and hyps[0].street_part.upper() == case[0].upper():
            acertos_original += 1
            
    # SpaCy
    if nlp_crf:
        doc = nlp_crf(case[0])
        pred = ""
        for ent in doc.ents:
            if ent.label_ == "STREET":
                pred = ent.text
                break
        if pred.upper() == case[0].upper():
            acertos_spacy += 1
                
    # Viterbi
    if cutter_viterbi:
        res_viterbi = cutter_viterbi.parse(case[0])
        if res_viterbi.get("STREET") and res_viterbi.get("STREET").upper() == case[0].upper():
            acertos_viterbi += 1

print(f"Original (AddressCutter): {acertos_original/len(test_cases)*100:.2f}%")
print(f"SpaCy CRF 'A1': {acertos_spacy/len(test_cases)*100:.2f}%")
print(f"Viterbi CRF: {acertos_viterbi/len(test_cases)*100:.2f}%")

# Test Libpostal
if parse_address:
    hits_lp = 0
    for query, expected in test_cases:
        parsed = parse_address(query)
        roads = [val.upper() for val, label in parsed if label == "road"]
        pred = " ".join(roads)
        if pred == query.upper() or query.upper() in pred:
            hits_lp += 1
    print(f"Libpostal: {hits_lp/len(test_cases)*100:.2f}%")
