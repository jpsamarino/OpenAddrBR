"""
Tests for encoder - street name encoding via sentence transformer.

Run with each backend:
    pytest tests/unit/test_encoder.py -v                         # all backends
    pytest tests/unit/test_encoder.py -v -k pytorch              # only pytorch
    pytest tests/unit/test_encoder.py -v -k pytorch-compiled   # only compiled
"""

import pytest
import numpy as np
from openaddrbr.services._encoder import (
    configure_encoder,
    _encode_street,
    _encode_streets_batch,
    VALID_BACKENDS,
)


# All backends except cuda (no GPU in CI)
BACKENDS_UNDER_TEST = tuple(b for b in VALID_BACKENDS if b != "cuda")


@pytest.fixture(autouse=True)
def reset_encoder():
    """Reset encoder before each test."""
    configure_encoder("pytorch-compiled")
    yield
    # Reset to default after test
    configure_encoder("pytorch-compiled")


@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_encode_street_returns_vector(backend):
    """Single street encoding returns a numpy array with correct shape."""
    configure_encoder(backend)
    result = _encode_street("rua marcelina")
    assert result is not None
    assert isinstance(result, np.ndarray)
    assert result.shape == (768,)


@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_encode_streets_batch_returns_array(backend):
    """Batch street encoding returns a 2D numpy array with shape (n, 768)."""
    configure_encoder(backend)
    streets = ["rua marcelina", "av paulista", "rua augusta"]
    result = _encode_streets_batch(streets, batch_size=2)
    assert isinstance(result, np.ndarray)
    assert result.shape == (3, 768)


@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_encode_street_empty_returns_none(backend):
    """Empty string encoding returns None."""
    configure_encoder(backend)
    result = _encode_street("")
    assert result is None


@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_encode_streets_batch_empty_returns_empty(backend):
    """Empty list encoding returns empty list."""
    configure_encoder(backend)
    result = _encode_streets_batch([], batch_size=32)
    assert result == []


@pytest.mark.parametrize("backend", BACKENDS_UNDER_TEST)
def test_encode_streets_batch_respects_batch_size(backend):
    """Batch encoding respects the batch_size parameter."""
    configure_encoder(backend)
    streets = ["rua " + str(i) for i in range(10)]
    result = _encode_streets_batch(streets, batch_size=4)
    # All streets should be encoded (10 rows, 768 dims)
    assert result.shape == (10, 768)


def test_configure_encoder_invalid_raises():
    """Configuring an invalid backend raises ValueError."""
    with pytest.raises(ValueError):
        configure_encoder("invalid-backend")


def test_configure_encoder_valid_backends():
    """configure_encoder accepts all valid backend names."""
    for backend in VALID_BACKENDS:
        configure_encoder(backend)  # Should not raise
