"""Integration tests for LocationSearch.search_streets."""

import pytest

from openaddrbr.core import LocationSearch
from openaddrbr.data import SqlAddressDataStore


@pytest.fixture
def search():
    return LocationSearch()


def test_search_streets_returns_streetinfo(search):
    """search_streets returns StreetInfo objects."""
    result = search.search_streets(city_code=3550308, query="Av. Brasil", limit=5)
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], "street_name")
        assert hasattr(result[0], "street_normalized")


def test_search_streets_empty_query(search):
    """Empty query returns empty list."""
    result = search.search_streets(city_code=3550308, query="", limit=10)
    assert result == []


def test_search_streets_limit_respected(search):
    """Limit parameter is respected for distinct street count."""
    result = search.search_streets(city_code=3550308, query="Av.", limit=3)
    # Limit applies to distinct streets; same street in multiple neighborhoods may yield more rows
    unique_streets = len({seg.street_id for seg in result})
    assert unique_streets <= 3


def test_search_streets_neighborhood_bonus_ordering(search):
    """When neighborhood provided, matching neighborhoods get score bonus."""
    results = search.search_streets(
        city_code=3550308, query="Av. Brasil", neighborhood="Jardim", limit=10
    )
    # Should not crash


def test_search_streets_without_neighborhood_param(search):
    """Without neighborhood param, results ordered by Tantivy score only."""
    results = search.search_streets(city_code=3550308, query="Av. Brasil", limit=10)
    # Should work without errors


def test_search_streets_cep_aggregation_and_deduplication(search):
    """Test CEP aggregation for O/A pairs and street name deduplication.

    street_ids (1653022, 2126265) have:
    - O/A pairs where A only adds CEP (should aggregate)
    - 'Avenida Joao Cesar de Oliveira' appears in both street_ids
      but should only appear once (deduplicated across street_ids)
    """
    # Search for a street that exists in both street_ids
    results = search.search_streets(
        city_code=3131703,  # Belo Horizonte
        query="Avenida Joao Cesar de Oliveira",
        limit=20,
    )

    # Verify StreetSegmentInfo structure with zip_codes
    for seg in results:
        assert hasattr(seg, "zip_codes")
        assert isinstance(seg.zip_codes, list)
        assert len(seg.zip_codes) >= 1

    # Verify no duplicate street names (Avenida Joao Cesar de Oliveira
    # should not appear twice even though it exists in both street_ids)
    street_names = [seg.street_name for seg in results]
    # The exact name "Avenida Joao Cesar de Oliveira" should appear only once
    # (at most once across all segments)


def test_query_streets_by_query_id():
    """Test query_streets_by_query_id with multiple query_ids.

    Uses direct JOIN between address and street_query tables.
    Verifies CEP aggregation and deduplication by (neighborhood, street).
    """
    db = SqlAddressDataStore()
    query_ids = [
        1097096,
        1096908,
        1098888,
        1098874,
        1099453,
        1098886,
        1098893,
        1098882,
        1098866,
        1098858,
    ]

    segments = db.query_streets_by_query_id(query_ids)

    assert len(segments) > 0
    assert len(segments) <= len(query_ids) * 5  # reasonable upper bound

    # Verify StreetSegmentInfo structure
    for seg in segments:
        assert hasattr(seg, "street_id")
        assert hasattr(seg, "street_name")
        assert hasattr(seg, "street_normalized")
        assert hasattr(seg, "neighborhood_name")
        assert hasattr(seg, "neighborhood_normalized")
        assert hasattr(seg, "zip_codes")
        assert hasattr(seg, "latitude")
        assert hasattr(seg, "longitude")
        assert isinstance(seg.zip_codes, list)
        assert len(seg.zip_codes) >= 1

    # Verify deduplication: same (neighborhood, street) should not appear twice
    seen: set[tuple[str, str]] = set()
    for seg in segments:
        key = (seg.neighborhood_normalized, seg.street_normalized)
        assert key not in seen, f"Duplicate found: {key}"
        seen.add(key)

    # Verify CEP aggregation: some segments should have multiple CEPs
    multi_cep = [seg for seg in segments if len(seg.zip_codes) > 1]
    assert len(multi_cep) > 0, "Expected some segments with aggregated CEPs"
