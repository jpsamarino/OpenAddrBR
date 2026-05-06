"""Encoder - sentence transformer model for street name encoding."""

from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from openaddrbr.data._config import get_model_path

MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Get or create the sentence transformer model."""
    global _model
    if _model is None:
        model_path = get_model_path()
        if not model_path.exists():
            print(f"[MODEL] Downloading model to {model_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_model = SentenceTransformer(MODEL_NAME)
            tmp_model.save(str(model_path))
            print(f"[MODEL] Model saved to local path")
        _model = SentenceTransformer(str(model_path))
        _model.max_seq_length = 128
    return _model


def _encode_street(street_norm: str) -> np.ndarray | None:
    """Encode a single street name to vector."""
    if not street_norm:
        return None
    model = _get_model()
    return model.encode([street_norm], show_progress_bar=False)[0]


def _encode_streets_batch(street_norms: list[str], batch_size: int) -> list[np.ndarray]:
    """Batch encode street names."""
    if not street_norms:
        return []
    return _get_model().encode(
        street_norms, batch_size=batch_size, show_progress_bar=False
    )
