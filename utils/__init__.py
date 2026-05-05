"""Compatibility shim - re-export from openaddrbr.utils."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

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