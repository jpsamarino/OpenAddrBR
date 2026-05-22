"""Encoder — sentence transformer model management."""

import logging
import shutil
import tempfile
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from openaddrbr.core.env import get_default_backend, get_default_batch_size, get_model_path

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
    Model is loaded in __init__ to fail fast and reserve memory upfront.
    """

    def __init__(self, backend: str | None = None, batch_size: int | None = None):
        self.backend = backend or get_default_backend()
        if self.backend not in VALID_BACKENDS:
            raise ValueError(f"Unknown backend: {backend}. Valid: {VALID_BACKENDS}")
        self._batch_size = batch_size if batch_size is not None else get_default_batch_size()
        self._model: SentenceTransformer = self._build_model()

    def _build_model(self) -> SentenceTransformer:
        """Load model synchronously in __init__."""
        import warnings

        warnings.filterwarnings(
            "ignore", message=".*torch.tensor results are registered as constants.*"
        )
        warnings.filterwarnings("ignore", message=".*incorrect regex pattern.*")
        warnings.filterwarnings(
            "ignore", message=".*torch.jit.script_method is deprecated.*"
        )

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
            return self._build_onnx_int8(model_path, onnx_int8_path)
        if self.backend == "onnx":
            return self._build_onnx_float(model_path, onnx_float_path)
        if self.backend == "pytorch-compiled":
            return self._build_pytorch_compiled(model_path)
        return self._build_pytorch(model_path)

    def _build_onnx_int8(self, model_path: Path, onnx_int8_path: Path) -> SentenceTransformer:
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
        model = SentenceTransformer(
            str(onnx_int8_path),
            backend="onnx",
            model_kwargs={"file_name": "onnx/model.onnx"},
        )
        model.max_seq_length = 128
        return model

    def _build_onnx_float(self, model_path: Path, onnx_float_path: Path) -> SentenceTransformer:
        if not onnx_float_path.exists():
            print(f"[MODEL] Exporting ONNX float32 to {onnx_float_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            base = SentenceTransformer(str(model_path), backend="onnx")
            base.save_pretrained(str(onnx_float_path))
            print(f"[MODEL] ONNX float32 exported")
        print(f"[MODEL] Loading ONNX float32 from {onnx_float_path}")
        model = SentenceTransformer(str(onnx_float_path), backend="onnx")
        model.max_seq_length = 128
        return model

    def _build_pytorch(self, model_path: Path) -> SentenceTransformer:
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16)")
            model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU")
            model = SentenceTransformer(str(model_path))
        model.max_seq_length = 128
        return model

    def _build_pytorch_compiled(self, model_path: Path) -> SentenceTransformer:
        if torch.cuda.is_available():
            print(f"[MODEL] Loading PyTorch on GPU (float16) + torch.compile")
            model = SentenceTransformer(
                str(model_path),
                device="cuda",
                dtype=torch.float16,
            )
        else:
            print(f"[MODEL] Loading PyTorch on CPU + torch.compile")
            model = SentenceTransformer(str(model_path))
        if hasattr(torch, "compile") and torch.compile is not None:
            try:
                model = torch.compile(model, mode="reduce-overhead")
                print(f"[MODEL] torch.compile applied")
            except Exception:
                pass
        model.max_seq_length = 128
        return model

    def encode(self, text: str) -> np.ndarray | None:
        """Encode a single street name to vector."""
        if not text:
            return None
        return self._model.encode([text], show_progress_bar=False)[0]

    def encode_batch(
        self,
        texts: list[str],
        batch_size: int | None = None,
    ) -> list[np.ndarray]:
        """Batch encode street names."""
        if not texts:
            return []
        if batch_size is None:
            batch_size = self._batch_size
        return self._model.encode(texts, batch_size=batch_size, show_progress_bar=False)