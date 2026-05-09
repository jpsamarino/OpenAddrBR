"""Compatibility - use openaddrbr.utils."""

from openaddrbr.utils._matching import make_similarity_func, text_similarity
from openaddrbr.utils._text import text_to_ascii

__all__ = ["text_similarity", "make_similarity_func", "text_to_ascii"]
