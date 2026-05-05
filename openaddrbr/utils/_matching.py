"""Address matching utilities."""

from rapidfuzz import fuzz
from openaddrbr.utils._text import text_to_ascii
from openaddrbr.core.models import StreetCluster


def text_similarity(
    text1: str, text2: str, case_sensitive: bool = True, ascii: bool = False
) -> float:
    """
    Similarity between two texts using rapidfuzz ratio.

    Args:
        text1: First text to compare.
        text2: Second text to compare.
        case_sensitive: Whether comparison is case-sensitive.
        ascii: Whether to normalize to ASCII (remove accents).

    Returns:
        Similarity score between 0.0 and 1.0.
    """
    t1 = text1 or ""
    t2 = text2 or ""

    if ascii:
        t1 = text_to_ascii(t1)
        t2 = text_to_ascii(t2)

    if not case_sensitive:
        t1 = t1.upper()
        t2 = t2.upper()

    if not t1 or not t2:
        return 0.0

    return fuzz.ratio(t1, t2) / 100


def make_similarity_func(normalize_func=None):
    """
    Factory that creates a similarity function with fixed normalization.

    Args:
        normalize_func: Optional function to normalize text before comparison.

    Returns:
        A similarity function with fixed normalization.
    """
    def similarity(text1: str, text2: str) -> float:
        t1 = normalize_func(text1) if normalize_func else (text1 or "")
        t2 = normalize_func(text2) if normalize_func else (text2 or "")
        if not t1 or not t2:
            return 0.0
        return fuzz.ratio(t1, t2) / 100
    return similarity


def find_best_street_match(
    clusters: list[StreetCluster],
    ref_street_norm: str,
    ref_neighborhood_norm: str,
    min_street_similarity: float = 0.7,
    min_neighborhood_similarity: float = 0.7,
    similarity_func=text_similarity,
) -> StreetCluster | None:
    """
    Find the best matching StreetCluster given reference street and neighborhood.

    Args:
        clusters: List of StreetCluster to search.
        ref_street_norm: Normalized reference street name.
        ref_neighborhood_norm: Normalized reference neighborhood name.
        min_street_similarity: Minimum street similarity threshold.
        min_neighborhood_similarity: Minimum neighborhood similarity threshold.
        similarity_func: Function to compute text similarity.

    Returns:
        Best matching StreetCluster or None if no match found.
    """
    weight_street = 0.7
    weight_neighborhood = 1.0 - weight_street
    best_cluster = None
    best_total_score = 0.0

    for summary in clusters:
        best_s_sim = max(
            (
                similarity_func(ref_street_norm, s or "")
                for s in summary.street_normalized
            ),
            default=0.0,
        )

        if best_s_sim > min_street_similarity:
            best_n_sim = max(
                (
                    similarity_func(ref_neighborhood_norm, n or "")
                    for n in summary.neighborhood_normalized
                ),
                default=1.0 if not ref_neighborhood_norm else 0.0,
            )

            if best_n_sim > min_neighborhood_similarity:
                total_score = (
                    weight_street * best_s_sim + weight_neighborhood * best_n_sim
                ) / (weight_street + weight_neighborhood)
                if total_score > best_total_score:
                    best_total_score = total_score
                    best_cluster = summary

    return best_cluster