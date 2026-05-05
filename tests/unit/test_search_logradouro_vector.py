"""
Tests for search_vector method using IBGEGeocoder.
Returns list of unique street_normalized names.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"


def get_embedding(text: str) -> np.ndarray:
    """Helper to compute embedding."""
    model = SentenceTransformer(MODEL_NAME)
    model.max_seq_length = 128
    return model.encode([text], show_progress_bar=False)[0]


class TestSearchVector:
    """Tests for search_vector using real usearch index."""

    def test_search_av_paulista_sao_paulo(self):
        """Should find AVENIDA PAULISTA in São Paulo."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("AVENIDA PAULISTA")
        results = coder.search_vector(emb, city_code)

        assert results is not None
        assert len(results) > 0
        assert isinstance(results, list)
        assert all(isinstance(r, str) for r in results)
        first = results[0].upper()
        assert "PAULISTA" in first

    def test_search_abbreviated_street(self):
        """Should find full street name from abbreviated input."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("AV PAULISTA")
        results = coder.search_vector(emb, city_code)

        assert results is not None
        assert len(results) > 0
        found = False
        for r in results:
            if "PAULISTA" in r.upper():
                found = True
                break
        assert found, "Should find Paulista street from AV PAULISTA query"

    def test_search_rua_augusta(self):
        """Should find RUA AUGUSTA or similar in São Paulo."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("RUA AUGUSTA")
        results = coder.search_vector(emb, city_code)

        assert results is not None
        assert len(results) > 0
        found = False
        for r in results:
            if "AUGUST" in r.upper():
                found = True
                break
        assert found, f"Should find AUGUST-related street, got: {results[:3]}"

    def test_search_with_limit(self):
        """Should respect limit parameter."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("AVENIDA PAULISTA")
        results = coder.search_vector(emb, city_code, limit=5)

        assert len(results) <= 5

    def test_search_returns_unique_names(self):
        """Should return unique street names (deduplicated)."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("AVENIDA PAULISTA")
        results = coder.search_vector(emb, city_code)

        assert len(results) == len(set(results))
        assert all(isinstance(r, str) for r in results)

    def test_search_partial_name(self):
        """Should find streets with partial name match."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()
        city_code = 3550308

        emb = get_embedding("PAULISTA")
        results = coder.search_vector(emb, city_code)

        assert results is not None
        assert len(results) > 0
        found = False
        for r in results:
            if "PAULISTA" in r.upper():
                found = True
                break
        assert found
