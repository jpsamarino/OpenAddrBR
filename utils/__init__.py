"""Compatibility shim - re-export from openaddrbr.utils."""

from openaddrbr.utils import (
    find_best_street_match,
    make_similarity_func,
    text_similarity,
    text_to_ascii,
)

__all__ = [
    "text_similarity",
    "find_best_street_match",
    "text_to_ascii",
    "make_similarity_func",
]
