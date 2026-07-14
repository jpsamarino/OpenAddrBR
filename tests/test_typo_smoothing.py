import pytest
import tempfile
import json
import os

from openaddrbr.core._address_cutter import AddressCutter

def test_typo_smoothing():
    dummy_data = {
        "tokens": {
            "JOSE": {
                "street": {
                    "single": {"qt_entities": 1000, "qt_addresses": 1000, "mean": 1.0, "std": 0.0}
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name

    try:
        cutter = AddressCutter(json_path, oov_penalty=-10.0)
        
        # Test typo match (adicionando 'DUMMY' no final para evitar o desconto do último token)
        score_typo = cutter._score_street(['JSE', 'DUMMY'], 0, 1)
        score_oov = cutter._score_street(['BOGUS', 'DUMMY'], 0, 1)
        
        # OOV should get -10, JSE should get typo_penalty(-2.0) + weight + LLR
        assert score_typo > score_oov
        assert score_oov <= -10.0
        assert score_typo > -9.0

    finally:
        os.unlink(json_path)
