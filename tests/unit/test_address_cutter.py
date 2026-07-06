import os
import json
import tempfile
from openaddrbr.core._address_cutter import AddressCutter

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
        assert "COSTA" in cutter.stats
        assert cutter.stats["COSTA"]["street"]["end"].std == 0.5
    finally:
        os.unlink(json_path)
