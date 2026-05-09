"""Compatibility shim - re-export from openaddrbr.utils."""

from openaddrbr.utils import (
    text_similarity,
    find_best_street_match,
    text_to_ascii,
    make_similarity_func,
)

__all__ = [
    "text_similarity",
    "find_best_street_match",
    "text_to_ascii",
    "make_similarity_func",
]