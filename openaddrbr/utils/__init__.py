"""Utils package for text normalization and matching."""

from openaddrbr.utils._matching import (
    find_best_street_match,
    make_similarity_func,
    text_similarity,
)
from openaddrbr.utils._text import normalize_text, text_to_ascii

__all__ = [
    "text_to_ascii",
    "normalize_text",
    "text_similarity",
    "find_best_street_match",
    "make_similarity_func",
]
