import pytest
import tempfile
import json
import os

from openaddrbr.core._address_cutter import AddressCutter
from openaddrbr.core.models._models import Pos, Role

def test_anti_drop_prefix_fallback():
    dummy_data = {
        "tokens": {
            "PAULISTA": {
                "street": {
                    "end": {"qt_entities": 1, "qt_addresses": 1, "mean": 1.0, "std": 0.0}
                }
            }
        }
    }
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.json', mode='w', encoding='utf-8') as f:
        json.dump(dummy_data, f)
        json_path = f.name

    try:
        cutter = AddressCutter(json_path)
        cutter.stats[("BLA", Role.STREET, Pos.END)] = cutter.stats[("PAULISTA", Role.STREET, Pos.END)]
        
        score_start = cutter._score_street(['PAULISTA', 'BLA'], 0, 2)
        assert score_start > cutter.oov_penalty

        score_single = cutter._score_street(['PAULISTA'], 0, 1)
        assert score_single > cutter.oov_penalty

    finally:
        os.unlink(json_path)
