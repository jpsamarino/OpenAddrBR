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

def normalize_for_compare(text: str) -> str:
    """Normalize text for comparison - remove accents and lowercase."""
    import unicodedata
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if c.isalnum() or c.isspace()).strip()

def contains_normalized(city_names: list[str], search: str) -> bool:
    """Check if any city name matches search term when normalized."""
    search_norm = normalize_for_compare(search)
    for name in city_names:
        if search_norm in normalize_for_compare(name):
            return True
    return False

def test_search_centro_sao_paulo(geocoder):
    """Searching 'centro' in São Paulo should return Centro neighborhood."""
    results = geocoder.search_neighborhood("centro", city_code=3550308, limit=10)
    assert len(results) > 0
    names = [r.neighborhood_name for r in results]
    assert contains_normalized(names, "Centro"), f"Expected 'Centro' in results: {names}"

def test_search_jardim_sao_paulo(geocoder):
    """Searching 'jardim' in São Paulo should return Jardim neighborhoods."""
    results = geocoder.search_neighborhood("jardim", city_code=3550308, limit=5)
    assert len(results) > 0
    names = [r.neighborhood_name for r in results]
    assert contains_normalized(names, "Jardim"), f"Expected 'Jardim' in results: {names}"

def test_search_vila_sao_paulo(geocoder):
    """Searching 'vila' in São Paulo should return Vila neighborhoods."""
    results = geocoder.search_neighborhood("vila", city_code=3550308, limit=5)
    assert len(results) > 0
    names = [r.neighborhood_name for r in results]
    assert contains_normalized(names, "Vila"), f"Expected 'Vila' in results: {names}"

def test_search_parque_sao_paulo(geocoder):
    """Searching 'parque' in São Paulo should return Parque neighborhoods."""
    results = geocoder.search_neighborhood("parque", city_code=3550308, limit=5)
    assert len(results) > 0
    names = [r.neighborhood_name for r in results]
    assert contains_normalized(names, "Parque"), f"Expected 'Parque' in results: {names}"

def test_search_results_have_valid_coordinates(geocoder):
    """All results should have valid Brazil coordinates."""
    results = geocoder.search_neighborhood("jardim", city_code=3550308, limit=5)
    for r in results:
        # Brazil lat: -33 to 5, lon: -73 to -34
        assert -35 <= r.latitude <= 5, f"Invalid latitude: {r.latitude}"
        assert -75 <= r.longitude <= -32, f"Invalid longitude: {r.longitude}"

def test_search_limit_respected(geocoder):
    """Search limit should be respected."""
    results = geocoder.search_neighborhood("centro", city_code=3550308, limit=3)
    assert len(results) <= 3

def test_search_returns_neighborhoodinfo_with_all_fields(geocoder):
    """Results should be NeighborhoodInfo with all required fields."""
    results = geocoder.search_neighborhood("centro", city_code=3550308, limit=5)
    if results:
        r = results[0]
        assert r.city_code == 3550308
        assert r.neighborhood_name
        assert r.neighborhood_normalized
        assert r.latitude != 0.0 or r.longitude != 0.0