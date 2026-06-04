"""Integration tests for LocationSearch.search_streets."""
import pytest

from openaddrbr.core import LocationSearch


@pytest.fixture
def search():
    return LocationSearch()


def test_search_streets_returns_streetinfo(search):
    """search_streets returns StreetInfo objects."""
    result = search.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], 'street_name')
        assert hasattr(result[0], 'street_normalized')


def test_search_streets_empty_query(search):
    """Empty query returns empty list."""
    result = search.search_streets(city_code=3550308, query="", limit=10)
    assert result == []


def test_search_streets_limit_respected(search):
    """Limit parameter is respected."""
    result = search.search_streets(city_code=3550308, query="Av.", limit=3)
    assert len(result) <= 3
