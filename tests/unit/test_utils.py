"""Tests for text utilities - TDD approach."""


from openaddrbr.core.models import StreetCluster
from openaddrbr.utils._matching import find_best_street_match, text_similarity
from openaddrbr.utils._text import text_to_ascii


class TestTextToAscii:
    """Tests for text_to_ascii utility."""

    def test_accented_a(self):
        """Á, À, Ã, Â should become A."""
        assert text_to_ascii("São") == "Sao"
        assert text_to_ascii("CAFÉ") == "CAFE"

    def test_accented_e(self):
        """É, È, Ê should become E."""
        assert text_to_ascii("José") == "Jose"

    def test_accented_o(self):
        """Ó, Ò, Õ, Ô should become O."""
        assert text_to_ascii("São Paulo") == "Sao Paulo"

    def test_cedilha(self):
        """Ç should become C."""
        assert text_to_ascii("Praça") == "Praca"

    def test_empty_string(self):
        """Empty string should return empty."""
        assert text_to_ascii("") == ""

    def test_none_input(self):
        """None input should return empty."""
        assert text_to_ascii(None) == ""


class TestTextSimilarity:
    """Tests for text_similarity with case_sensitive and ascii parameters."""

    def test_identical_strings(self):
        """Identical strings should return 1.0."""
        result = text_similarity("AVENIDA PAULISTA", "AVENIDA PAULISTA")
        assert result == 1.0

    def test_exact_match(self):
        """Exact match returns high similarity."""
        result = text_similarity("RUA DAS FLORES", "RUA DAS FLORES")
        assert result >= 0.9

    def test_abbreviated_vs_full(self):
        """AV will match AVENIDA with good similarity."""
        result = text_similarity("AV PAULISTA", "AVENIDA PAULISTA")
        assert result >= 0.7

    def test_completely_different(self):
        """Completely different strings should have low similarity."""
        result = text_similarity("RUA DAS FLORES", "AVENIDA BRASIL")
        assert result < 0.5

    def test_empty_first_string(self):
        """Empty first string returns 0.0."""
        result = text_similarity("", "AVENIDA PAULISTA")
        assert result == 0.0

    def test_none_first(self):
        """None as first string returns 0.0."""
        result = text_similarity(None, "AVENIDA PAULISTA")
        assert result == 0.0

    def test_ascii_normalization(self):
        """ASCII normalization removes accents."""
        result = text_similarity("SÃO PAULO", "SAO PAULO", ascii=True)
        assert result >= 0.9


class TestFindBestStreetMatch:
    """Tests for find_best_street_match."""

    def make_cluster(self, street_id: int, streets: list, neighborhoods: list) -> StreetCluster:
        """Helper to create StreetCluster."""
        return StreetCluster(
            street_id=street_id,
            street_normalized=set(streets),
            neighborhood_normalized=set(neighborhoods),
        )

    def test_exact_match(self):
        """Exact street and neighborhood match."""
        clusters = [
            self.make_cluster(1, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
            self.make_cluster(2, ["RUA AUGUSTA"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "BELA VISTA")
        assert result.street_id == 1

    def test_partial_street_match(self):
        """Partial street match but correct neighborhood."""
        clusters = [
            self.make_cluster(1, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
            self.make_cluster(2, ["RUA AUGUSTA"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AV PAULISTA", "BELA VISTA")
        assert result.street_id == 1

    def test_wrong_neighborhood_no_match(self):
        """Correct street but wrong neighborhood - should not match."""
        clusters = [
            self.make_cluster(1, ["AVENIDA PAULISTA"], ["JARDIM PAULISTA"]),
            self.make_cluster(2, ["RUA AUGUSTA"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "CENTRO")
        assert result is None

    def test_empty_clusters(self):
        """Empty list of clusters returns None."""
        result = find_best_street_match([], "AVENIDA PAULISTA", "BELA VISTA")
        assert result is None

    def test_multiple_clusters_best_match(self):
        """Multiple clusters - best overall match wins."""
        clusters = [
            self.make_cluster(1, ["RUA DAS ROSAS"], ["JARDIM"]),
            self.make_cluster(2, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
            self.make_cluster(3, ["RUA DO CARMO"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "BELA VISTA")
        assert result.street_id == 2
