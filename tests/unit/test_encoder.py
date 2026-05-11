"""Tests for Encoder class."""

import numpy as np
import pytest

from openaddrbr.core._encoder import VALID_BACKENDS, Encoder


class TestEncoder:
    def test_init_with_default_backend(self):
        encoder = Encoder()
        assert encoder.backend in VALID_BACKENDS

    def test_init_with_custom_backend(self):
        encoder = Encoder(backend="onnx")
        assert encoder.backend == "onnx"

    def test_init_invalid_backend_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            Encoder(backend="invalid")

    def test_encode_none_for_empty_text(self):
        encoder = Encoder()
        result = encoder.encode("")
        assert result is None

    def test_backend_is_stored(self):
        encoder = Encoder(backend="pytorch-compiled")
        assert encoder.backend == "pytorch-compiled"
