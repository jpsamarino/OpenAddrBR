"""Utils package for text normalization and matching."""

from openaddrbr.utils._text import text_to_ascii, normalize_text
from openaddrbr.utils._matching import (
    text_similarity,
    find_best_street_match,
    make_similarity_func,
)

__all__ = [
    "text_to_ascii",
    "normalize_text",
    "text_similarity",
    "find_best_street_match",
    "make_similarity_func",
]
