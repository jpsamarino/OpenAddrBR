"""Encoder — sentence transformer model management."""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from openaddrbr.core._env import get_default_backend, get_default_batch_size, get_model_path

# Silence spurious tokenizer warnings
for _logger_name in ["transformers", "sentence_transformers", "onnxruntime", "optimum"]:
    _logger = logging.getLogger(_logger_name)
    _logger.setLevel(logging.ERROR)
    _logger.propagate = False

MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

EncoderBackend = str  # Literal["pytorch", "pytorch-compiled", "onnx-int8", "onnx", "cuda"]
VALID_BACKENDS = ("pytorch", "pytorch-compiled", "onnx-int8", "onnx", "cuda")


class Encoder:
    """Sentence transformer encoder with configurable backend.

    Thread-safe: model is loaded once and shared across threads.
    """

    def __init__(self, backend: str | None = None):
        self.backend = backend or get_default_backend()
        if self.backend not in VALID_BACKENDS:
            raise ValueError(f"Unknown backend: {backend}. Valid: {VALID_BACKENDS}")
        self._model: Optional[SentenceTransformer] = None

    def _get_model(self) -> SentenceTransformer:
        """Lazy load the model."""
        if self._model is not None:
            return self._model

        import warnings

        warnings.filterwarnings(
            "ignore", message=".*torch.tensor results are registered as constants.*"
        )
        warnings.filterwarnings("ignore", message=".*incorrect regex pattern.*")

        model_path = get_model_path()
        if not model_path.exists():
            print(f"[MODEL] Downloading model to {model_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_model = SentenceTransformer(MODEL_NAME)
            tmp_model.save(str(model_path))
            print(f"[MODEL] Model saved to local path")

        onnx_int8_path = model_path.parent / "onnx-int8"
        onnx_float_path = model_path.parent / "onnx-float32"

        if self.backend == "onnx-int8":
            return self._load_onnx_int8(model_path, onnx_int8_path)
        if self.backend == "onnx":
            return self._load_onnx_float(model_path, onnx_float_path)
        if self.backend == "pytorch-compiled":
            return self._load_pytorch_compiled(model_path)
        # pytorch or cuda
        return self._load_pytorch(model_path)

    def _load_onnx_int8(self, model_path: Path, onnx_int8_path: Path) -> SentenceTransformer:
        from sentence_transformers import export_dynamic_quantized_onnx_model

        if not onnx_int8_path.exists():
            print(f"[MODEL] Exporting ONNX int8 to {onnx_int8_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            base = SentenceTransformer(str(model_path), backend="onnx")
            base.save_pretrained(str(onnx_int8_path))
            with tempfile.TemporaryDirectory() as tmpdir:
                export_dynamic_quantized_onnx_model(base, "avx2", tmpdir)
                quant_onnx = Path(tmpdir) / "onnx" / "model_quint8_avx2.onnx"
                target_onnx = onnx_int8_path / "onnx" / "model.onnx"
                shutil.copy2(quant_onnx, target_onnx)
            print(f"[MODEL] ONNX int8 exported")
        print(f"[MODEL] Loading ONNX int8 from {onnx_int8_path}")
        self._model = SentenceTransformer(
            str(onnx_int8_path),
            backend="onnx",
            model_kwargs={"file_name": "onnx/model.onnx"},
        )
        self._model.max_seq_length = 128
        return self._model

    def _load_onnx_float(self, model_path: Path, onnx_float_path: Path) -> SentenceTransformer:
        if not onnx_float_path.exists():
            print(f"[MODEL] Exporting ONNX float32 to {onnx_float_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            base = SentenceTransformer(str(model_path), backend="onnx")
            base.save_pretrained(str(onnx_float_path))
            print(f"[MODEL] ONNX float32 exported")
        print(f"[MODEL] Loading ONNX float32 from {onnx_float_path}")
        self._model = SentenceTransformer(str(onnx_float_path), backend="onnx")
        self._model.max_seq_length = 128
        return self._model

    def _load_pytorch(self, model_path: Path) -> SentenceTransformer:
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16)")
            self._model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU")
            self._model = SentenceTransformer(str(model_path))
        self._model.max_seq_length = 128
        return self._model

    def _load_pytorch_compiled(self, model_path: Path) -> SentenceTransformer:
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16) + torch.compile")
            self._model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU + torch.compile")
            self._model = SentenceTransformer(str(model_path))
        if hasattr(torch, "compile") and torch.compile is not None:
            try:
                self._model = torch.compile(self._model, mode="reduce-overhead")
                print(f"[MODEL] torch.compile applied")
            except Exception:
                pass
        self._model.max_seq_length = 128
        return self._model

    def encode(self, text: str) -> np.ndarray | None:
        """Encode a single street name to vector."""
        if not text:
            return None
        model = self._get_model()
        return model.encode([text], show_progress_bar=False)[0]

    def encode_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[np.ndarray]:
        """Batch encode street names."""
        if not texts:
            return []
        if batch_size is None:
            batch_size = get_default_batch_size()
        return self._get_model().encode(texts, batch_size=batch_size, show_progress_bar=False)
