"""Unit tests for TextSearchEngine.search_streets."""
import pytest

from openaddrbr.data import TextSearchEngine


@pytest.fixture
def engine():
    return TextSearchEngine()


def test_search_streets_returns_search_hits(engine):
    """search_streets returns list of SearchHit objects."""
    result = engine.search_streets("av brasil", city_code=3550308, limit=10)
    assert isinstance(result, list)
    if result:
        assert hasattr(result[0], 'score')
        assert hasattr(result[0], 'doc_address')


def test_search_streets_empty_query(engine):
    """Empty query returns empty list."""
    result = engine.search_streets("", city_code=3550308, limit=10)
    assert result == []


def test_search_streets_limit_respected(engine):
    """Limit parameter is respected."""
    result = engine.search_streets("av", city_code=3550308, limit=5)
    assert len(result) <= 5
