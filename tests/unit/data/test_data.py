"""Tests for data layer - TDD approach."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "d:/projetos/OpenAddrBR")

import pytest
from unittest.mock import MagicMock, patch


class TestConfig:
    """Tests for data path configuration."""

    def test_get_data_path_default(self):
        """Default path should be ~/.openaddrbr/data"""
        from openaddrbr.data._config import get_data_path, DEFAULT_DATA_DIR

        path = get_data_path()
        assert "openaddrbr" in str(path).lower()
        assert path == DEFAULT_DATA_DIR

    def test_set_data_path(self):
        """Setting custom path should override default."""
        from openaddrbr.data._config import set_data_path, get_data_path

        custom_path = "/custom/path"
        set_data_path(custom_path)
        # Compare as Path objects to handle cross-platform path separators
        assert get_data_path() == Path(custom_path)

    def test_get_sgeodb_path(self):
        """sgeodb path should be data_path/sgeobr.db"""
        from openaddrbr.data._config import get_sgeodb_path, set_data_path

        set_data_path("/test/data")
        sgeodb = get_sgeodb_path()
        assert str(sgeodb).endswith("sgeobr.db")

    def test_get_usearch_dir(self):
        """usearch dir should be data_path/usearch_v2"""
        from openaddrbr.data._config import get_usearch_dir, set_data_path

        set_data_path("/test/data")
        usearch = get_usearch_dir()
        assert str(usearch).endswith("usearch_v2")


class TestDatabase:
    """Tests for database operations (mocked)."""

    def test_query_address_by_cep_returns_rows(self):
        """query_address_by_cep should return list of rows with street_id, normalized names."""
        from openaddrbr.data._db import query_address_by_cep

        with patch("openaddrbr.data._db.get_connection") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchall.return_value = [
                {"street_id": 1, "street_normalized": "RUA DAS FLORES", "neighborhood_normalized": "CENTRO"},
            ]

            rows = query_address_by_cep("01310000", limit=10)
            assert len(rows) == 1
            assert rows[0]["street_id"] == 1

    def test_query_address_by_cep_empty_result(self):
        """query_address_by_cep should return empty list when no results."""
        from openaddrbr.data._db import query_address_by_cep

        with patch("openaddrbr.data._db.get_connection") as mock_conn:
            mock_conn.return_value.execute.return_value.fetchall.return_value = []

            rows = query_address_by_cep("00000000")
            assert rows == []


class TestHuggingFaceDownloader:
    """Tests for HuggingFace download."""

    def test_check_data_exists_returns_bool(self):
        """check_data_exists should return True/False."""
        from openaddrbr.data._hf_downloader import check_data_exists

        # Without actual data, should return False (unless data exists in test env)
        # This tests the function exists and returns a boolean
        result = check_data_exists()
        assert isinstance(result, bool)