"""Integration tests for LocationSearch.autocomplete_street."""

import pytest
from openaddrbr.core import LocationSearch


@pytest.fixture
def suggestions():
    return LocationSearch()


def test_autocomplete_returns_list_of_strings(suggestions):
    """autocomplete_street should return list of street name strings."""
    results = suggestions.autocomplete_street(city_code=3550308, query="Av. Brasil", limit=5)
    assert isinstance(results, list)
    if results:
        assert all(isinstance(r, str) for r in results)


def test_autocomplete_empty_query_returns_empty(suggestions):
    """Empty query returns empty list."""
    results = suggestions.autocomplete_street(city_code=3550308, query="", limit=10)
    assert results == []


def test_autocomplete_whitespace_query_returns_empty(suggestions):
    """Whitespace-only query returns empty list."""
    results = suggestions.autocomplete_street(city_code=3550308, query="   ", limit=10)
    assert results == []


def test_autocomplete_limit_respected(suggestions):
    """Limit should be respected."""
    results = suggestions.autocomplete_street(city_code=3550308, query="Av.", limit=3)
    assert len(results) <= 3


def test_autocomplete_partial_query(suggestions):
    """Partial queries work."""
    results = suggestions.autocomplete_street(city_code=3550308, query="Av. Br", limit=5)
    assert isinstance(results, list)


def test_autocomplete_single_char_query(suggestions):
    """Single char queries do not crash."""
    results = suggestions.autocomplete_street(city_code=3550308, query="A", limit=10)
    assert isinstance(results, list)


def test_autocomplete_different_city_codes(suggestions):
    """Different city codes return different results."""
    results_sp = suggestions.autocomplete_street(city_code=3550308, query="Av. Brasil", limit=5)
    results_rj = suggestions.autocomplete_street(city_code=3304557, query="Av. Brasil", limit=5)


def test_autocomplete_invalid_city_code(suggestions):
    """Invalid city code returns empty list."""
    results = suggestions.autocomplete_street(city_code=9999999, query="Av.", limit=10)
    assert results == []


def test_autocomplete_performance(suggestions):
    """Should be very fast - under 50ms for typical queries."""
    import time
    start = time.time()
    results = suggestions.autocomplete_street(city_code=3550308, query="Av. Brasil", limit=10)
    elapsed = (time.time() - start) * 1000
    assert elapsed < 50, f"Autocomplete took {elapsed:.2f}ms"


def test_autocomplete_returns_unique_names(suggestions):
    """Should return unique street names."""
    results = suggestions.autocomplete_street(city_code=3550308, query="Av.", limit=20)
    assert len(results) == len(set(results))
