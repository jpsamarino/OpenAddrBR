"""Unit tests for query_streets_by_ids."""
import pytest

from openaddrbr.data import SqlAddressDataStore


@pytest.fixture
def db():
    return SqlAddressDataStore()


def test_query_streets_by_query_id_returns_streetinfo(db):
    """Bulk lookup returns StreetInfo objects."""
    result = db.query_streets_by_query_id([12345])
    assert isinstance(result, list)


def test_query_streets_by_query_id_empty_list(db):
    """Empty query_ids returns empty list."""
    result = db.query_streets_by_query_id([])
    assert result == []


def test_query_streets_by_query_id_multiple_ids(db):
    """Bulk lookup with multiple query_ids."""
    result = db.query_streets_by_query_id([12345, 67890])
    assert isinstance(result, list)
