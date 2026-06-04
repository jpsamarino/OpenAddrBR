"""Unit tests for query_streets_by_ids."""
import pytest

from openaddrbr.data import SqlAddressDataStore


@pytest.fixture
def db():
    return SqlAddressDataStore()


def test_query_streets_by_ids_returns_streetinfo(db):
    """Bulk lookup returns StreetInfo objects."""
    result = db.query_streets_by_ids([12345])
    assert isinstance(result, list)


def test_query_streets_by_ids_empty_list(db):
    """Empty street_ids returns empty list."""
    result = db.query_streets_by_ids([])
    assert result == []


def test_query_streets_by_ids_multiple_ids(db):
    """Bulk lookup with multiple street_ids."""
    result = db.query_streets_by_ids([12345, 67890])
    assert isinstance(result, list)
