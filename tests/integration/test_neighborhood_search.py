import pytest
from openaddrbr import Geocoder, NeighborhoodInfo

@pytest.fixture
def geocoder():
    return Geocoder()

def test_search_neighborhood_returns_list(geocoder):
    results = geocoder.search_neighborhood("centro", city_code=3550308, limit=5)
    assert isinstance(results, list)

def test_search_neighborhood_returns_neighborhoodinfo(geocoder):
    results = geocoder.search_neighborhood("jardim", city_code=3550308, limit=3)
    if results:
        assert isinstance(results[0], NeighborhoodInfo)

def test_search_neighborhood_has_required_fields(geocoder):
    results = geocoder.search_neighborhood("centro", city_code=3550308, limit=5)
    if results:
        r = results[0]
        assert hasattr(r, 'neighborhood_name')
        assert hasattr(r, 'neighborhood_normalized')
        assert hasattr(r, 'city_code')
        assert hasattr(r, 'latitude')
        assert hasattr(r, 'longitude')

def test_search_neighborhood_empty_query_returns_empty(geocoder):
    results = geocoder.search_neighborhood("", city_code=3550308, limit=10)
    assert results == []