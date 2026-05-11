"""Tests for Database class."""

from unittest.mock import MagicMock, patch

import pytest

from openaddrbr.core._database import CityRecord, Database


class TestDatabase:
    def test_init_with_default_path(self):
        db = Database()
        assert db._db_path is not None

    def test_init_with_custom_path(self, tmp_path):
        db = Database(data_path=tmp_path)
        assert db._db_path is not None

    def test_city_cache_miss(self):
        db = Database()
        # Force no cached value
        result = db.get_city_info_from_db("NonExistent", "XX")
        assert result is None

    def test_is_multi_street_cep_not_cached(self):
        db = Database()
        # Should not raise even if DB not present
        result = db.is_multi_street_cep("00000000")
        assert isinstance(result, bool)

    def test_close_clears_cursors(self):
        db = Database()
        db._cursors = {123: MagicMock()}
        db._conn = MagicMock()
        db.close()
        assert db._cursors == {}
        assert db._conn is None
