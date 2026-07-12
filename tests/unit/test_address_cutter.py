import os
import json
import tempfile
from openaddrbr.core._address_cutter import AddressCutter
from openaddrbr.core.models._models import AddressKey, Role, Pos

def test_address_cutter_initialization():
    dummy_data = {
        "tokens": {
            "COSTA": {
                "street": {
                    "end": {"qt_entities": 2, "qt_addresses": 50, "mean": 3.0, "std": 0.0}
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name

    try:
        cutter = AddressCutter(json_path)
        assert "COSTA" in cutter.weights
        assert AddressKey("COSTA", Role.STREET, Pos.END) in cutter.stats
        assert cutter.stats[AddressKey("COSTA", Role.STREET, Pos.END)].std == 3.5
    finally:
        os.unlink(json_path)

def test_scoring_methods():
    dummy_data = {
        "tokens": {
            "RUA": { "street": { "start": {"qt_entities": 100, "qt_addresses": 50, "mean": 3.0, "std": 1.0} } },
            "COSTA": { "street": { "end": {"qt_entities": 50, "qt_addresses": 50, "mean": 3.0, "std": 0.0} } }
        }
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name
    try:
        cutter = AddressCutter(json_path)
        # Test street scoring (tokens, start, end)
        score_street = cutter._score_street(["RUA", "HORTA", "COSTA"], 0, 3)
        assert score_street < 0  # "HORTA" is OOV so it gets penalized, but score_street computes successfully
        
        # Test transition scoring (tokens, start, end, has_any_digit)
        score_trans = cutter._score_transition(["RUA", "HORTA", "COSTA", "123"], 3, 4, True)
        assert score_trans == cutter.house_number_bonus
    finally:
        os.unlink(json_path)

def test_cut_method():
    dummy_data = {
        "tokens": {
            "RUA": { "street": { "start": {"qt_entities": 100, "qt_addresses": 50, "mean": 3.0, "std": 1.0} } },
            "COSTA": { "street": { "end": {"qt_entities": 50, "qt_addresses": 50, "mean": 3.0, "std": 0.0} } }
        }
    }
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name
    try:
        cutter = AddressCutter(json_path)
        
        # Test 1: Hard Cut by Comma (asserts rest_part is stripped)
        cuts = cutter.cut("RUA HORTA COSTA, 123 ALV")
        assert len(cuts) == 1
        assert cuts[0].street_part == "RUA HORTA COSTA"
        assert cuts[0].rest_part == "123 ALV"
        
        # Test 2: Statistical sliding - Numbers evaluated by probability
        cuts = cutter.cut("RUA HORTA COSTA 123 ALV")
        assert len(cuts) > 1
        assert cuts[0].street_part == "RUA HORTA COSTA"
        assert cuts[0].rest_part == "123 ALV"
    finally:
        os.unlink(json_path)
