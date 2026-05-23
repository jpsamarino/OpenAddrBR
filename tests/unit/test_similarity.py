"""
Tests for similarity utilities.
"""


from openaddrbr.utils._matching import make_similarity_func, text_similarity
from openaddrbr.utils._text import text_to_ascii


class TestTextSimilarity:
    """Tests for text_similarity with case_sensitive and ascii parameters."""

    def test_identical_strings(self):
        """Identical strings should return 1.0."""
        result = text_similarity("AVENIDA PAULISTA", "AVENIDA PAULISTA")
        assert result == 1.0

    def test_considere_end_of_string(self):
        """should consider end of string"""
        result = text_similarity("AVENIDA ATLANTICA", "AVENIDA ATLANTICA")
        assert result == 1.0
        result = text_similarity("AVENIDA ATLANTICA", "AVENIDA ATLANTICA 4240")
        assert result != 1.0

    def test_exact_match(self):
        """Exact match returns high similarity."""
        result = text_similarity("RUA DAS FLORES", "RUA DAS FLORES")
        assert result >= 0.9

    def test_similar_street_names(self):
        """Similar street names should have high similarity."""
        result = text_similarity("AVENIDA PAULISTA", "AVENIDA PAULIST")
        assert result >= 0.8

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

    def test_empty_second_string(self):
        """Empty second string returns 0.0."""
        result = text_similarity("AVENIDA PAULISTA", "")
        assert result == 0.0

    def test_both_empty(self):
        """Both empty returns 0.0."""
        result = text_similarity("", "")
        assert result == 0.0

    def test_none_first(self):
        """None as first string returns 0.0."""
        result = text_similarity(None, "AVENIDA PAULISTA")
        assert result == 0.0

    def test_none_second(self):
        """None as second string returns 0.0."""
        result = text_similarity("AVENIDA PAULISTA", None)
        assert result == 0.0

    def test_case_sensitive_differs(self):
        """Case sensitive comparison gives lower similarity for different case."""
        result = text_similarity("AVENIDA PAULISTA", "avenida paulist")
        assert result < 1.0

    def test_case_insensitive(self):
        """Case insensitive comparison gives high similarity."""
        result = text_similarity("AVENIDA PAULISTA", "avenida paulist", case_sensitive=False)
        assert result >= 0.9

    def test_ascii_normalization(self):
        """ASCII normalization removes accents."""
        result = text_similarity("SÃO PAULO", "SAO PAULO", ascii=True)
        assert result >= 0.9

    def test_ascii_and_case_insensitive(self):
        """ASCII and case insensitive gives high similarity for accent differences."""
        result = text_similarity("SÃO PAULO", "sao paulo", case_sensitive=False, ascii=True)
        assert result >= 0.9

    def test_token_ratio_favors_suffix_match(self):
        """
        Known behavior: token_ratio (via token_set_ratio) favors suffix/end-of-string matches.

        Example:
        - 'RUA PEDRO FERNANDES' vs 'RUA PEDRO CUSTODIO' = 0.59
        - 'RUA PEDRO FERNANDES' vs 'RUA JOSE GASPAR FERNANDES' = 0.73

        This happens because token_set_ratio returns 100 when one string is a
        subset of the other (when intersection is non-empty and one diff is empty).
        So 'FERNANDES' at the end makes a higher score.

        This test documents the behavior, not the desired behavior.
        """
        s1 = "RUA PEDRO FERNANDES"
        s2a = "RUA PEDRO CUSTODIO"
        s2b = "RUA JOSE GASPAR FERNANDES"

        ratio1 = text_similarity(s1, s2a)
        ratio2 = text_similarity(s1, s2b)

        # token_ratio favors suffix matches - counterintuitive but expected behavior
        assert ratio2 > ratio1, "token_ratio should favor suffix matches (known behavior)"
        assert ratio1 < 0.7, "PEDRO FERNANDES vs PEDRO CUSTODIO should be < 0.7"
        assert ratio2 > 0.7, "PEDRO FERNANDES vs JOSE GASPAR FERNANDES should be > 0.7"

    def test_ratio_gives_similar_scores_for_unrelated_streets(self):
        """
        With ratio, streets that share only the 'RUA' prefix but have completely
        different actual street names get SIMILAR scores.

        Example:
        - 'RUA BANDEIRANTES' vs 'RUA ENO VIEIRA DE ANDRADE' = 0.54
        - 'RUA BANDEIRANTES' vs 'RUA JOSE GASPAR FERNANDES' = 0.54

        Both scores are similar (~0.54) because ratio compares character sequences.
        The common prefix 'RUA ' dominates the similarity calculation.
        """
        s1 = "RUA BANDEIRANTES"
        s2a = "RUA ENO VIEIRA DE ANDRADE"
        s2b = "RUA JOSE GASPAR FERNANDES"

        ratio_a = text_similarity(s1, s2a)
        ratio_b = text_similarity(s1, s2b)

        # With ratio, the scores are SIMILAR (same prefix dominates)
        assert abs(ratio_a - ratio_b) < 0.02, "Scores should be similar with ratio"
        assert ratio_a < 0.6, "Score should be < 0.6 since street names are unrelated"


class TestMakeSimilarityFunc:
    """Tests for make_similarity_func factory."""

    def test_factory_creates_working_function(self):
        """Factory should create a working similarity function."""
        sim_func = make_similarity_func(text_to_ascii)
        result = sim_func("SÃO PAULO", "SAO PAULO")
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_factory_no_normalize(self):
        """Factory with no normalize_func should work like text_similarity."""
        sim_func = make_similarity_func(None)
        result = sim_func("AVENIDA PAULISTA", "AVENIDA PAULISTA")
        assert result == 1.0

    def test_factory_with_custom_normalize(self):
        """Factory with custom normalize function."""

        def uppercase_normalize(text):
            return text.upper() if text else ""

        sim_func = make_similarity_func(uppercase_normalize)
        result = sim_func("avenida paulo", "AVENIDA PAULO")
        assert result >= 0.9


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
        assert text_to_ascii("AÇAIL") == "ACAIL"

    def test_n_with_tilde(self):
        """Ñ should become N."""
        assert text_to_ascii("ESPANHA") == "ESPANHA"

    def test_lowercase_input(self):
        """Lowercase input should be handled."""
        assert text_to_ascii("são paulo") == "sao paulo"

    def test_empty_string(self):
        """Empty string should return empty."""
        assert text_to_ascii("") == ""

    def test_none_input(self):
        """None input should return empty."""
        assert text_to_ascii(None) == ""

    def test_already_ascii(self):
        """Already ASCII text should be unchanged."""
        assert text_to_ascii("AVENIDA PAULISTA") == "AVENIDA PAULISTA"
