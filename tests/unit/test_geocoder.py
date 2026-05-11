"""Tests for Geocoder class."""

import pytest
from unittest.mock import MagicMock, patch

from openaddrbr.core._geocoder import Geocoder


class TestGeocoder:
    def test_init_with_defaults(self):
        geocoder = Geocoder()
        assert geocoder.encoder is not None
        assert geocoder.db is not None
        assert geocoder.batch_size > 0

    def test_init_with_custom_encoder(self):
        mock_encoder = MagicMock()
        geocoder = Geocoder(encoder=mock_encoder)
        assert geocoder.encoder is mock_encoder

    def test_init_with_custom_db(self):
        mock_db = MagicMock()
        geocoder = Geocoder(db=mock_db)
        assert geocoder.db is mock_db

    def test_init_with_custom_backend(self):
        geocoder = Geocoder(backend="onnx")
        assert geocoder.encoder.backend == "onnx"

    def test_init_with_custom_data_path(self, tmp_path):
        geocoder = Geocoder(data_path=tmp_path)
        assert geocoder.db is not None

    def test_geocode_returns_none_for_unknown_city(self):
        mock_encoder = MagicMock()
        mock_db = MagicMock()
        geocoder = Geocoder(encoder=mock_encoder, db=mock_db)
        with patch("openaddrbr.core._geocoder.get_city_info", return_value=None):
            result = geocoder.geocode("Rua X", "Centro", "UnknownCity", "XX")
        assert result is None