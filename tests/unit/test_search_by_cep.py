"""
Tests for search_by_cep method using IBGEGeocoder.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from domain.models import StreetCluster


class TestSearchByCep:
    """Tests for search_by_cep method using IBGEGeocoder."""

    def test_integration(self):
        """Should return street_cluster when exact match found."""
        from application import IBGEGeocoder

        coder = IBGEGeocoder()

        result = coder.search_by_cep("01310000", "AVENIDA PAULISTA", "BELA VISTA")

        assert result is not None
        assert result.street_id == 2840120

    def test_exact_match(self):
        """Should return street_cluster when exact match found."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "BELA VISTA",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AVENIDA PAULISTA", "BELA VISTA")

            assert result is not None
            assert result.street_id == 1

    def test_partial_match(self):
        """Should return street_cluster when partial match found."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "BELA VISTA",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AV PAULISTA", "BELA VISTA")

            assert result is not None
            assert result.street_id == 1

    def test_no_match(self):
        """Should return None when no match found."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "RUA DAS FLORES",
                    "neighborhood_normalized": "JARDIM",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AVENIDA BRASIL", "CENTRO")

            assert result is None

    def test_empty_result(self):
        """Should return None when database returns empty."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = []

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("00000000", "AVENIDA PAULISTA", "BELA VISTA")

            assert result is None

    def test_multiple_street_ids(self):
        """Should return best matching street_cluster among multiple."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "RUA DAS ROSAS",
                    "neighborhood_normalized": "JARDIM",
                },
                {
                    "street_id": 2,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "BELA VISTA",
                },
                {
                    "street_id": 3,
                    "street_normalized": "RUA DO CARMO",
                    "neighborhood_normalized": "CENTRO",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AVENIDA PAULISTA", "BELA VISTA")

            assert result is not None
            assert result.street_id == 2

    def test_multiple_variations_same_street(self):
        """Should find best match considering all variations of same street_id."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "BELA VISTA",
                },
                {
                    "street_id": 1,
                    "street_normalized": "AV. PAULISTA",
                    "neighborhood_normalized": "B. VISTA",
                },
                {
                    "street_id": 2,
                    "street_normalized": "RUA AUGUSTA",
                    "neighborhood_normalized": "CENTRO",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AV PAULISTA", "B. VISTA")

            assert result is not None
            assert result.street_id == 1

    def test_without_neighborhood(self):
        """Should work when neighborhood_norm is empty string."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "BELA VISTA",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AVENIDA PAULISTA", "")

            assert result is None

    def test_neighborhood_below_threshold(self):
        """Should not match when neighborhood similarity is below threshold."""
        with patch(
            "application.ibge_geocoder.IBGEGeocoder._get_sgeodb"
        ) as mock_get_db:
            mock_conn = MagicMock()
            mock_get_db.return_value = mock_conn

            mock_conn.execute.return_value.fetchall.return_value = [
                {
                    "street_id": 1,
                    "street_normalized": "AVENIDA PAULISTA",
                    "neighborhood_normalized": "JARDIM PAULISTA",
                },
            ]

            from application import IBGEGeocoder

            coder = IBGEGeocoder()

            result = coder.search_by_cep("01310000", "AVENIDA PAULISTA", "CENTRO")

            assert result is None
