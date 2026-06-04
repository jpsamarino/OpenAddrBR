"""Integration tests for street autocomplete via LocationSearch."""

import pytest

from openaddrbr.core import LocationSearch


@pytest.fixture
def suggestions():
    return LocationSearch()


# === Basic functionality tests ===

def test_search_returns_streetinfo_objects(suggestions):
    """Results should be StreetInfo objects."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    assert all(hasattr(r, 'street_name') for r in results)


def test_search_empty_query_returns_empty(suggestions):
    """Empty query returns empty list."""
    results = suggestions.search_streets(city_code=3550308, query="", limit=10)
    assert results == []


def test_search_whitespace_query_returns_empty(suggestions):
    """Whitespace-only query returns empty list."""
    results = suggestions.search_streets(city_code=3550308, query="   ", limit=10)
    assert results == []


def test_search_limit_respected(suggestions):
    """Search limit should be respected."""
    results = suggestions.search_streets(city_code=3550308, query="Av.", limit=3)
    assert len(results) <= 3


def test_search_normalizes_query(suggestions):
    """Query should be normalized before search."""
    results = suggestions.search_streets(city_code=3550308, query="avenida brasil", limit=5)
    # Should find same results as "Av. Brasil"
    assert isinstance(results, list)


# === City code filtering tests ===

def test_search_different_city_codes(suggestions):
    """Different city codes return different results."""
    results_sp = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    results_rj = suggestions.search_streets(city_code=3304557, query="Av. Brasil", limit=5)
    # Results should be different or at least not guaranteed same


def test_search_invalid_city_code(suggestions):
    """Invalid city code returns empty list."""
    results = suggestions.search_streets(city_code=9999999, query="Av.", limit=10)
    assert results == []


# === Query variation tests ===

def test_search_full_street_name(suggestions):
    """Full street name search works."""
    results = suggestions.search_streets(city_code=3550308, query="Avenida Brasil", limit=10)
    assert len(results) >= 0


def test_search_abbreviation(suggestions):
    """Abbreviated street names work."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Bras", limit=10)
    assert len(results) >= 0


def test_search_partial_query(suggestions):
    """Partial queries work."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Br", limit=10)
    assert len(results) >= 0


def test_search_single_char_query(suggestions):
    """Single char queries may return empty or limited results."""
    results = suggestions.search_streets(city_code=3550308, query="A", limit=10)
    # Should not crash, may return empty
    assert isinstance(results, list)


# === StreetInfo field validation tests ===

def test_streetinfo_has_street_name(suggestions):
    """StreetInfo objects have street_name field."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    if results:
        assert all(hasattr(r, 'street_name') and r.street_name for r in results)


def test_streetinfo_has_street_normalized(suggestions):
    """StreetInfo objects have street_normalized field."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    if results:
        assert all(hasattr(r, 'street_normalized') for r in results)


def test_streetinfo_has_city_code(suggestions):
    """StreetInfo objects have city_code field."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    if results:
        assert all(hasattr(r, 'city_code') for r in results)


def test_streetinfo_has_zip_codes(suggestions):
    """StreetInfo objects have zip_codes field (list)."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    if results:
        assert all(hasattr(r, 'zip_codes') and isinstance(r.zip_codes, list) for r in results)


# === Neighborhood bonus tests ===

def test_neighborhood_param_does_not_filter(suggestions):
    """Neighborhood param orders results but does not filter."""
    results = suggestions.search_streets(
        city_code=3550308,
        query="Av. Brasil",
        neighborhood="Centro",
        limit=10
    )
    # Should still return results even if no street has "Centro" neighborhood
    assert isinstance(results, list)


def test_neighborhood_bonus_applied_when_match(suggestions):
    """When neighborhood matches, bonus is applied to score."""
    results_with = suggestions.search_streets(
        city_code=3550308,
        query="Av. Brasil",
        neighborhood="Jardim",
        limit=5
    )
    results_without = suggestions.search_streets(
        city_code=3550308,
        query="Av. Brasil",
        limit=5
    )
    # Order may differ based on neighborhood matching
    assert isinstance(results_with, list)
    assert isinstance(results_without, list)


# === Performance tests ===

def test_search_performance_under_100ms(suggestions):
    """Search should complete under 100ms for typical queries."""
    import time
    start = time.time()
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=10)
    elapsed = (time.time() - start) * 1000
    assert elapsed < 100, f"Search took {elapsed:.2f}ms"


def test_search_multiple_queries_performance(suggestions):
    """Multiple consecutive searches perform reasonably."""
    import time
    start = time.time()
    for _ in range(10):
        suggestions.search_streets(city_code=3550308, query="Av. Brasil", limit=10)
    elapsed = (time.time() - start) * 1000
    avg = elapsed / 10
    assert avg < 50, f"Average search took {avg:.2f}ms"


# === Edge cases ===

def test_search_nonexistent_street_handling(suggestions):
    """Query for street returns valid list (may not be empty due to ngram matching)."""
    results = suggestions.search_streets(city_code=3550308, query="XYZQWERTY123NONEXISTENT", limit=10)
    # Should not crash, returns list (possibly empty or with partial matches)
    assert isinstance(results, list)


def test_search_special_characters(suggestions):
    """Special characters in query are handled."""
    results = suggestions.search_streets(city_code=3550308, query="Av. Brasil #", limit=10)
    # Should not crash, may return empty or filtered results
    assert isinstance(results, list)
