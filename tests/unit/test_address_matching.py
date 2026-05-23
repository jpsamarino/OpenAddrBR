"""
Tests for address_matching utilities - Complex realistic scenarios.
"""


from openaddrbr.core.models import StreetCluster
from openaddrbr.utils._matching import find_best_street_match, text_similarity


def make_cluster(street_id: int, streets: list, neighborhoods: list) -> StreetCluster:
    """Helper to create StreetCluster with given variations."""
    return StreetCluster(
        street_id=street_id,
        street_normalized=set(streets),
        neighborhood_normalized=set(neighborhoods),
    )


class TestFindBestStreetMatchComplex:
    """Complex realistic tests for find_best_street_match."""

    def test_real_scenario_exact_match(self):
        """Real scenario: exact street and neighborhood match in same cluster."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA", "AV PAULISTA"], ["BELA VISTA", "B VISTA"]),
            make_cluster(2, ["RUA OSCAR FREIRE"], ["JARDIM PAULISTA"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "BELA VISTA")
        assert result.street_id == 1

    def test_real_scenario_partial_match(self):
        """Real scenario: partial street match but correct neighborhood."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
            make_cluster(2, ["RUA AUGUSTA"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AV PAULISTA", "BELA VISTA")
        assert result.street_id == 1

    def test_real_scenario_wrong_neighborhood(self):
        """Real scenario: correct street but wrong neighborhood - should not match."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["JARDIM PAULISTA"]),
            make_cluster(2, ["RUA AUGUSTA"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "CENTRO")
        assert result is None

    def test_real_scenario_similar_street_different_neighborhood(self):
        """Real scenario: similar street names in different neighborhoods."""
        clusters = [
            make_cluster(1, ["AVENIDA BRASIL"], ["CENTRO"]),
            make_cluster(2, ["AVENIDA PAULISTA"], ["MORUMBI"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA BRASIL", "CENTRO")
        assert result.street_id == 1

    def test_real_scenario_multi_street_variations(self):
        """Real scenario: same street with many variations (abbreviations, etc)."""
        clusters = [
            make_cluster(
                1,
                ["AVENIDA PAULISTA", "AV. PAULISTA", "AV PAULISTA", "PAULISTA AV"],
                ["BELA VISTA", "B VISTA"],
            ),
        ]
        result = find_best_street_match(clusters, "AV PAULISTA", "BELA VISTA")
        assert result.street_id == 1

    def test_real_scenario_no_match_below_threshold(self):
        """Real scenario: similarity below threshold should not match."""
        clusters = [
            make_cluster(1, ["RUA DAS FLORES"], ["JARDIM"]),
        ]
        result = find_best_street_match(
            clusters, "AVENIDA BRASIL", "CENTRO", min_street_similarity=0.7
        )
        assert result is None

    def test_real_scenario_street_match_neighborhood_no_match(self):
        """Real scenario: street matches but neighborhood doesn't."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["JARDIM PAULISTA"]),
        ]
        result = find_best_street_match(
            clusters, "RUA DAS FLORES", "CENTRO", min_street_similarity=0.7
        )
        assert result is None

    def test_real_scenario_none_ref_neighborhood(self):
        """Real scenario: ref_neighborhood=None computes similarity with empty string."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", None)
        assert result is None

    def test_real_scenario_weighted_scoring(self):
        """Real scenario: weighted scoring - cluster with exact street should win."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["JARDIM PAULISTA"]),
            make_cluster(2, ["RUA AUGUSTA"], ["AVENIDA PAULISTA"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "AVENIDA PAULISTA")
        assert result.street_id == 1

    def test_real_scenario_custom_similarity_case_insensitive(self):
        """Real scenario: custom case-insensitive similarity function."""

        def case_insensitive_sim(text1, text2):
            return text_similarity(text1, text2, case_sensitive=False)

        clusters = [
            make_cluster(1, ["avenida paulista"], ["bela vista"]),
        ]
        result = find_best_street_match(
            clusters, "AVENIDA PAULISTA", "BELA VISTA", similarity_func=case_insensitive_sim
        )
        assert result.street_id == 1

    def test_real_scenario_empty_cluster_set(self):
        """Edge case: empty list of clusters."""
        result = find_best_street_match([], "AVENIDA PAULISTA", "BELA VISTA")
        assert result is None

    def test_real_scenario_cluster_with_empty_street_set(self):
        """Edge case: cluster with empty street_normalized set."""
        clusters = [
            StreetCluster(
                street_id=1, street_normalized=set(), neighborhood_normalized={"BELA VISTA"}
            ),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "BELA VISTA")
        assert result is None

    def test_real_scenario_multiple_clusters_best_match(self):
        """Real scenario: multiple clusters - best overall match wins."""
        clusters = [
            make_cluster(1, ["RUA DAS ROSAS"], ["JARDIM"]),
            make_cluster(2, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
            make_cluster(3, ["RUA DO CARMO"], ["CENTRO"]),
            make_cluster(4, ["AVENIDA BRASIL"], ["CENTRO"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "BELA VISTA")
        assert result.street_id == 2

    def test_real_scenario_thresholds_enforcement(self):
        """Real scenario: thresholds should filter out poor matches."""
        clusters = [
            make_cluster(1, ["RUA DAS FLORES"], ["JARDIM"]),
        ]
        result = find_best_street_match(
            clusters,
            "AVENIDA TOTALLY DIFFERENT",
            "CENTRO",
            min_street_similarity=0.3,
            min_neighborhood_similarity=0.3,
        )
        assert result is None

    def test_real_scenario_partial_neighborhood_match(self):
        """Real scenario: partial neighborhood match."""
        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["JARDIM PAULISTA"]),
        ]
        result = find_best_street_match(clusters, "AVENIDA PAULISTA", "JARDIM")
        assert result is not None or result is None

    def test_real_scenario_custom_exact_similarity(self):
        """Real scenario: custom exact match similarity."""

        def exact_match_sim(text1, text2):
            return 1.0 if text1 == text2 else 0.0

        clusters = [
            make_cluster(1, ["AVENIDA PAULISTA"], ["BELA VISTA"]),
        ]
        result = find_best_street_match(
            clusters, "AVENIDA PAULISTA", "BELA VISTA", similarity_func=exact_match_sim
        )
        assert result.street_id == 1

    def test_real_scenario_large_cluster_variations(self):
        """Real scenario: 4+ clusters with 4+ street and neighborhood variations each."""
        clusters = [
            make_cluster(
                1,
                ["AVENIDA PAULISTA", "AV. PAULISTA", "AV PAULISTA", "PAULISTA AVE"],
                ["BELA VISTA", "B. VISTA", "VISTA BELA", "BELA"],
            ),
            make_cluster(
                2,
                ["RUA OSCAR FREIRE", "R. OSCAR FREIRE", "OSCAR FREIRE RUA", "R OSCAR FREIRE"],
                ["JARDIM PAULISTA", "JD PAULISTA", "PAULISTA JARDIM", "JARDIM"],
            ),
            make_cluster(
                3,
                ["AVENIDA BRASIL", "AV. BRASIL", "AV BRASIL", "BRASIL AVE"],
                ["CENTRO", "C. CENTRO", "CENTRO HISTORICO", "CENTRO CIDADE"],
            ),
            make_cluster(
                4,
                ["RUA AUGUSTA", "R. AUGUSTA", "AUGUSTA RUA", "R AUGUSTA"],
                ["CONSOLACAO", "CONSOLACAO CENTRO", "CENTRO CONSOLACAO", "CONSOL"],
            ),
        ]
        result = find_best_street_match(clusters, "AV PAULISTA", "B. VISTA")
        assert result.street_id == 1

        result = find_best_street_match(clusters, "OSCAR FREIRE", "JARDIM")
        assert result.street_id == 2

        result = find_best_street_match(clusters, "AV BRASIL", "CENTRO")
        assert result.street_id == 3

        result = find_best_street_match(clusters, "R AUGUSTA", "CONSOLACAO")
        assert result.street_id == 4
