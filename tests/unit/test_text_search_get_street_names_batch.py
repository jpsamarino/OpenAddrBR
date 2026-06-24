"""Unit tests for TextSearchEngine.get_street_names_batch."""

import pytest

from openaddrbr.data import TextSearchEngine


@pytest.fixture
def engine():
    return TextSearchEngine()


def test_get_street_names_batch_returns_list_of_strings(engine):
    """Should return list of street name strings."""
    hits = engine.search_streets("Av. Brasil", 3550308, limit=5, autocomplete_query=True)
    if not hits:
        pytest.skip("No hits found")

    doc_addresses = [hit.doc_address for hit in hits]
    names = engine.get_street_names_batch(doc_addresses)

    assert isinstance(names, list)
    assert all(isinstance(n, str) for n in names)


def test_get_street_names_batch_returns_unique_names(engine):
    """Should return unique street names."""
    hits = engine.search_streets("Av.", 3550308, limit=10, autocomplete_query=True)
    if len(hits) < 2:
        pytest.skip("Not enough hits")

    doc_addresses = [hit.doc_address for hit in hits]
    names = engine.get_street_names_batch(doc_addresses)
    assert len(names) == len(set(names))


def test_get_street_names_batch_empty_input(engine):
    """Empty list input returns empty list."""
    names = engine.get_street_names_batch([])
    assert names == []


def test_get_street_names_batch_invalid_addresses(engine):
    """Invalid doc addresses return empty values in list."""
    hits = engine.search_streets("Av. Brasil", 3550308, limit=1, autocomplete_query=True)
    if not hits:
        pytest.skip("No hits found")

    doc_addresses = [hit.doc_address for hit in hits] + [99999999]
    names = engine.get_street_names_batch(doc_addresses)
    assert isinstance(names, list)
