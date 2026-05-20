"""Integration tests for city autocomplete search - human-like queries."""

import unicodedata

import pytest

from openaddrbr import CityInfo, Geocoder


@pytest.fixture
def geocoder():
    return Geocoder()


def normalize_for_compare(text: str) -> str:
    """Normalize text for comparison - remove accents and lowercase."""
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in text if c.isalnum() or c.isspace()).strip()


def contains_normalized(city_names: list[str], search: str) -> bool:
    """Check if any city name matches search term when normalized."""
    search_norm = normalize_for_compare(search)
    for name in city_names:
        if search_norm in normalize_for_compare(name):
            return True
    return False


def test_search_rio_de_returns_rio_de_janeiro(geocoder):
    """Searching 'rio de' should return Rio de Janeiro."""
    results = geocoder.search_city("rio de", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Rio de Janeiro"), (
        f"Expected 'Rio de Janeiro' in results: {city_names}"
    )


def test_search_cont_returns_contagem(geocoder):
    """Searching 'cont' should return Contagem."""
    results = geocoder.search_city("cont", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Contagem"), (
        f"Expected 'Contagem' in results: {city_names}"
    )


def test_search_sao_paulo_returns_sao_paulo(geocoder):
    """Searching 'sao paulo' should return São Paulo."""
    results = geocoder.search_city("sao paulo", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "São Paulo"), (
        f"Expected 'São Paulo' in results: {city_names}"
    )


def test_search_belo_horizonte_returns_belo_horizonte(geocoder):
    """Searching 'belo horizonte' should return Belo Horizonte."""
    results = geocoder.search_city("belo horizonte", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Belo Horizonte"), (
        f"Expected 'Belo Horizonte' in results: {city_names}"
    )


def test_search_curitiba_returns_curitiba(geocoder):
    """Searching 'curitiba' should return Curitiba."""
    results = geocoder.search_city("curitiba", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Curitiba"), (
        f"Expected 'Curitiba' in results: {city_names}"
    )


def test_search_florianopolis_returns_florianopolis(geocoder):
    """Searching 'florianopolis' should return Florianópolis."""
    results = geocoder.search_city("florianopolis", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Florianópolis"), (
        f"Expected 'Florianópolis' in results: {city_names}"
    )


def test_search_porto_alegre_returns_porto_alegre(geocoder):
    """Searching 'porto alegre' should return Porto Alegre."""
    results = geocoder.search_city("porto alegre", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Porto Alegre"), (
        f"Expected 'Porto Alegre' in results: {city_names}"
    )


def test_search_recife_returns_recife(geocoder):
    """Searching 'reci' should return Recife."""
    results = geocoder.search_city("reci", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Recife"), (
        f"Expected 'Recife' in results: {city_names}"
    )


def test_search_fortaleza_returns_fortaleza(geocoder):
    """Searching 'fort' should return Fortaleza."""
    results = geocoder.search_city("fort", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Fortaleza"), (
        f"Expected 'Fortaleza' in results: {city_names}"
    )


def test_search_goiania_returns_goiania(geocoder):
    """Searching 'goiania' should return Goiânia."""
    results = geocoder.search_city("goiania", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Goiânia"), (
        f"Expected 'Goiânia' in results: {city_names}"
    )


def test_search_campinas_returns_campinas(geocoder):
    """Searching 'camp' should return Campinas."""
    results = geocoder.search_city("camp", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Campinas"), (
        f"Expected 'Campinas' in results: {city_names}"
    )


def test_search_uberlandia_returns_uberlandia(geocoder):
    """Searching 'uber' should return Uberlândia."""
    results = geocoder.search_city("uber", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Uberlândia"), (
        f"Expected 'Uberlândia' in results: {city_names}"
    )


def test_search_natal_returns_natal(geocoder):
    """Searching 'natal' should return Natal."""
    results = geocoder.search_city("natal", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Natal"), (
        f"Expected 'Natal' in results: {city_names}"
    )


def test_search_maceio_returns_maceio(geocoder):
    """Searching 'mace' should return Maceió."""
    results = geocoder.search_city("mace", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Maceió"), (
        f"Expected 'Maceió' in results: {city_names}"
    )


def test_search_salvador_returns_salvador(geocoder):
    """Searching 'salv' should return Salvador."""
    results = geocoder.search_city("salv", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Salvador"), (
        f"Expected 'Salvador' in results: {city_names}"
    )


def test_search_brasilia_returns_brasilia(geocoder):
    """Searching 'brasilia' should return Brasília."""
    results = geocoder.search_city("brasilia", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Brasília"), (
        f"Expected 'Brasília' in results: {city_names}"
    )


def test_search_manaus_returns_manaus(geocoder):
    """Searching 'manaus' should return Manaus."""
    results = geocoder.search_city("manaus", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Manaus"), (
        f"Expected 'Manaus' in results: {city_names}"
    )


def test_search_results_have_valid_state_codes(geocoder):
    """All results should have valid Brazilian state codes."""
    results = geocoder.search_city("rio de", limit=10)
    valid_states = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
        "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }
    for r in results:
        assert r.state_code in valid_states, f"Invalid state code: {r.state_code}"


def test_search_results_have_valid_coordinates(geocoder):
    """All results should have valid Brazil coordinates."""
    results = geocoder.search_city("sao paulo", limit=5)
    for r in results:
        # Brazil lat: -33 to 5, lon: -73 to -34
        assert -35 <= r.latitude <= 5, f"Invalid latitude: {r.latitude}"
        assert -75 <= r.longitude <= -32, f"Invalid longitude: {r.longitude}"


def test_search_limit_respected(geocoder):
    """Search limit should be respected."""
    results = geocoder.search_city("sao paulo", limit=3)
    assert len(results) <= 3


def test_search_empty_returns_empty(geocoder):
    """Empty query returns empty list."""
    results = geocoder.search_city("", limit=10)
    assert results == []


def test_search_returns_cityinfo_objects(geocoder):
    """Results should be CityInfo objects with all fields."""
    results = geocoder.search_city("rio de", limit=5)
    assert all(isinstance(r, CityInfo) for r in results)
    for r in results:
        assert r.city_code > 0
        assert r.city_name
        assert r.city_normalized
        assert r.state_code
        assert r.latitude != 0 or r.longitude != 0  # coordinates available