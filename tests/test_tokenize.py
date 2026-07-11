import pytest
import os
import sys
import tempfile
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from openaddrbr.core._address_cutter import AddressCutter

@pytest.fixture
def cutter():
    # Mock data to ensure PAULISTA and KM2 are in weights
    dummy_data = {
        "tokens": {
            "PAULISTA": {
                "street": {
                    "start": {"qt_entities": 10, "qt_addresses": 10, "mean": 1.0, "std": 0.0}
                }
            },
            "PI": {
                "street": {
                    "start": {"qt_entities": 5, "qt_addresses": 5, "mean": 1.0, "std": 0.0}
                }
            },
            "KM2": {
                "street": {
                    "start": {"qt_entities": 5, "qt_addresses": 5, "mean": 1.0, "std": 0.0}
                }
            }
        }
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name
    
    cutter_obj = AddressCutter(json_path)
    os.unlink(json_path)
    return cutter_obj

def test_smart_split_adaptive(cutter):
    # Caso 1: Sufixo alfa curto conhecido como rua (ex: PAULISTA + 1A) -> Split
    # Assumindo "PAULISTA" existe no dict. 
    # Usando PI1A testará especificamente o vocabulário, pois len('PI') <= 2 (threshold default)
    
    # Original test requested:
    tokens1 = cutter._tokenize("PAULISTA1A")
    assert tokens1 == ["PAULISTA", "1", "A"] # split is fine as 3 parts
    
    # Adicionando PI para provar que a lógica nova de vocabulário funciona:
    tokens_pi = cutter._tokenize("PI1A")
    assert tokens_pi == ["PI", "1", "A"]
    
    # Caso 2: Token inteiro conhecido (ex: KM2) -> Não faz split
    # Assumindo "KM2" existe no dict
    tokens2 = cutter._tokenize("KM2")
    assert tokens2 == ["KM2"]
