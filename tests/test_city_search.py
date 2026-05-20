import pytest
from openaddrbr.services._city_search import search_city_tantivy
from openaddrbr.core.models import CityInfo


def test_search_city_returns_list():
    """Basic search should return list of CityInfo."""
    results = search_city_tantivy("Sao Paulo", limit=5)
    assert isinstance(results, list)


def test_search_city_contains_required_fields():
    """Each result should have all CityInfo fields."""
    results = search_city_tantivy("Rio", limit=3)
    if results:
        r = results[0]
        assert hasattr(r, 'city_code')
        assert hasattr(r, 'city_name')
        assert hasattr(r, 'city_normalized')
        assert hasattr(r, 'state_code')
        assert hasattr(r, 'latitude')
        assert hasattr(r, 'longitude')


def test_search_city_empty_query_returns_empty():
    """Empty query should return empty list."""
    results = search_city_tantivy("", limit=10)
    assert results == []


def test_search_city_limit_works():
    """limit parameter should cap results."""
    results = search_city_tantivy("Santo", limit=2)
    assert len(results) <= 2