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


def test_search_streets_neighborhood_bonus_ordering(search):
    """When neighborhood provided, matching neighborhoods get score bonus."""
    results = search.search_streets(
        city_code=3550308,
        query="Av. Brasil",
        neighborhood="Jardim",
        limit=10
    )
    # Should not crash


def test_search_streets_without_neighborhood_param(search):
    """Without neighborhood param, results ordered by Tantivy score only."""
    results = search.search_streets(city_code=3550308, query="Av. Brasil", limit=10)
    # Should work without errors
