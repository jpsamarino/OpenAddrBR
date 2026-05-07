"""Encoder - sentence transformer model for street name encoding."""

import os
from pathlib import Path
from typing import Literal, Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from openaddrbr.data._config import get_model_path

MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

EncoderBackend = Literal["pytorch", "pytorch-compiled", "onnx-int8", "onnx", "cuda"]
VALID_BACKENDS: tuple[EncoderBackend, ...] = ("pytorch", "pytorch-compiled", "onnx-int8", "onnx", "cuda")

_model: Optional[SentenceTransformer] = None
_configured_backend: Optional[EncoderBackend] = None


def configure_encoder(backend: EncoderBackend) -> None:
    """Configure encoder backend before first use.

    Must be called before any encode function.
    After model is loaded, this has no effect (set it before first encode).

    Args:
        backend: One of:
            - "pytorch" (plain PyTorch, no torch.compile, default if available)
            - "pytorch-compiled" (PyTorch with torch.compile)
            - "onnx-int8" (quantized ONNX, best for Apple Silicon or ARM)
            - "onnx" (ONNX float32)
            - "cuda" (PyTorch GPU, float16)

    Raises:
        ValueError: If backend is not recognized.

    Example:
        configure_encoder("onnx-int8")  # before first encode
        from openaddrbr.services._encoder import _encode_streets_batch
        vectors = _encode_streets_batch(streets, batch_size=16)
    """
    global _configured_backend
    if backend not in VALID_BACKENDS:
        raise ValueError(f"Unknown backend: {backend}. Valid: {VALID_BACKENDS}")
    _configured_backend = backend
    # Reset model so it reloads with new backend
    global _model
    _model = None


def _get_backend() -> EncoderBackend:
    """Resolve backend to use: configured > env var > default (pytorch)."""
    if _configured_backend:
        return _configured_backend
    return os.environ.get("OPENADDRBR_BACKEND", "pytorch").lower()  # type: ignore[return-value]


def _get_model() -> SentenceTransformer:
    """Get or create the sentence transformer model."""
    global _model

    if _model is not None:
        return _model

    model_path = get_model_path()
    if not model_path.exists():
        print(f"[MODEL] Downloading model to {model_path}...")
        model_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_model = SentenceTransformer(MODEL_NAME)
        tmp_model.save(str(model_path))
        print(f"[MODEL] Model saved to local path")

    backend = _get_backend()
    onnx_int8_path = model_path.parent / "onnx-int8"
    onnx_float_path = model_path.parent / "onnx-float32"

    # --- ONNX int8 ---
    if backend in ("onnx-int8",):
        from sentence_transformers import export_dynamic_quantized_onnx_model
        import tempfile
        import shutil as _shutil

        if not onnx_int8_path.exists():
            print(f"[MODEL] Exporting ONNX int8 to {onnx_int8_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            base = SentenceTransformer(
                str(model_path),
                backend="onnx",
                processor_kwargs={"fix_mistral_regex": True},
            )
            base.save_pretrained(str(onnx_int8_path))
            with tempfile.TemporaryDirectory() as tmpdir:
                export_dynamic_quantized_onnx_model(base, "avx2", tmpdir)
                quant_onnx = Path(tmpdir) / "onnx" / "model_quint8_avx2.onnx"
                target_onnx = onnx_int8_path / "onnx" / "model.onnx"
                _shutil.copy2(quant_onnx, target_onnx)
            print(f"[MODEL] ONNX int8 exported")
        print(f"[MODEL] Loading ONNX int8 from {onnx_int8_path}")
        _model = SentenceTransformer(
            str(onnx_int8_path),
            backend="onnx",
            model_kwargs={"file_name": "onnx/model.onnx"},
            processor_kwargs={"fix_mistral_regex": True},
        )
        _model.max_seq_length = 128
        return _model

    # --- ONNX float32 ---
    if backend in ("onnx",):
        if not onnx_float_path.exists():
            print(f"[MODEL] Exporting ONNX float32 to {onnx_float_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            base = SentenceTransformer(
                str(model_path),
                backend="onnx",
                processor_kwargs={"fix_mistral_regex": True},
            )
            base.save_pretrained(str(onnx_float_path))
            print(f"[MODEL] ONNX float32 exported")
        print(f"[MODEL] Loading ONNX float32 from {onnx_float_path}")
        _model = SentenceTransformer(
            str(onnx_float_path),
            backend="onnx",
            processor_kwargs={"fix_mistral_regex": True},
        )
        _model.max_seq_length = 128
        return _model

    # --- PyTorch compiled ---
    if backend == "pytorch-compiled":
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16) + torch.compile")
            _model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU + torch.compile")
            _model = SentenceTransformer(str(model_path))
        if hasattr(torch, "compile") and torch.compile is not None:
            try:
                _model = torch.compile(_model, mode="reduce-overhead")
                print(f"[MODEL] torch.compile applied")
            except Exception:
                pass
        _model.max_seq_length = 128
        return _model

    # --- PyTorch plain (no torch.compile) ---
    if backend == "pytorch":
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16)")
            _model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU")
            _model = SentenceTransformer(str(model_path))
        _model.max_seq_length = 128
        return _model

    # --- CUDA (explicit GPU) ---
    if backend == "cuda":
        print(f"[MODEL] Loading PyTorch on GPU (float16)")
        _model = SentenceTransformer(
            str(model_path),
            device="cuda",
            dtype=torch.float16,
        )
        _model.max_seq_length = 128
        return _model

    # Should not reach here
    raise ValueError(f"Unhandled backend: {backend}")


def _encode_street(street_norm: str) -> np.ndarray | None:
    """Encode a single street name to vector."""
    if not street_norm:
        return None
    model = _get_model()
    return model.encode([street_norm], show_progress_bar=False)[0]


def _encode_streets_batch(
    street_norms: list[str],
    batch_size: int | None = None,
) -> list[np.ndarray]:
    """Batch encode street names.

    Args:
        street_norms: List of normalized street names.
        batch_size: Batch size. If None, uses OPENADDRBR_BATCH_SIZE env var
                    or defaults to 16.
    """
    if not street_norms:
        return []
    if batch_size is None:
        batch_size = int(os.environ.get("OPENADDRBR_BATCH_SIZE", 16))
    return _get_model().encode(
        street_norms, batch_size=batch_size, show_progress_bar=False
    )