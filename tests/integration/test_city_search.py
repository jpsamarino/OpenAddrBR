"""Integration tests for city autocomplete via LocationSuggestions."""

import unicodedata

import pytest

from openaddrbr.core import LocationSuggestions
from openaddrbr.core.models import CityInfo


@pytest.fixture
def suggestions():
    return LocationSuggestions()


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


def test_search_rio_de_returns_rio_de_janeiro(suggestions):
    """Searching 'rio de' should return Rio de Janeiro."""
    results = suggestions.search_cities("rio de", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Rio de Janeiro"), (
        f"Expected 'Rio de Janeiro' in results: {city_names}"
    )


def test_search_cont_returns_contagem(suggestions):
    """Searching 'cont' should return Contagem."""
    results = suggestions.search_cities("cont", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Contagem"), (
        f"Expected 'Contagem' in results: {city_names}"
    )


def test_search_sao_paulo_returns_sao_paulo(suggestions):
    """Searching 'sao paulo' should return São Paulo."""
    results = suggestions.search_cities("sao paulo", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "São Paulo"), (
        f"Expected 'São Paulo' in results: {city_names}"
    )


def test_search_belo_horizonte_returns_belo_horizonte(suggestions):
    """Searching 'belo horizonte' should return Belo Horizonte."""
    results = suggestions.search_cities("belo horizonte", limit=10)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Belo Horizonte"), (
        f"Expected 'Belo Horizonte' in results: {city_names}"
    )


def test_search_curitiba_returns_curitiba(suggestions):
    """Searching 'curitiba' should return Curitiba."""
    results = suggestions.search_cities("curitiba", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Curitiba"), (
        f"Expected 'Curitiba' in results: {city_names}"
    )


def test_search_florianopolis_returns_florianopolis(suggestions):
    """Searching 'florianopolis' should return Florianópolis."""
    results = suggestions.search_cities("florianopolis", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Florianópolis"), (
        f"Expected 'Florianópolis' in results: {city_names}"
    )


def test_search_porto_alegre_returns_porto_alegre(suggestions):
    """Searching 'porto alegre' should return Porto Alegre."""
    results = suggestions.search_cities("porto alegre", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Porto Alegre"), (
        f"Expected 'Porto Alegre' in results: {city_names}"
    )


def test_search_recife_returns_recife(suggestions):
    """Searching 'reci' should return Recife."""
    results = suggestions.search_cities("reci", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Recife"), (
        f"Expected 'Recife' in results: {city_names}"
    )


def test_search_fortaleza_returns_fortaleza(suggestions):
    """Searching 'fort' should return Fortaleza."""
    results = suggestions.search_cities("fort", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Fortaleza"), (
        f"Expected 'Fortaleza' in results: {city_names}"
    )


def test_search_goiania_returns_goiania(suggestions):
    """Searching 'goiania' should return Goiânia."""
    results = suggestions.search_cities("goiania", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Goiânia"), (
        f"Expected 'Goiânia' in results: {city_names}"
    )


def test_search_campinas_returns_campinas(suggestions):
    """Searching 'camp' should return Campinas."""
    results = suggestions.search_cities("camp", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Campinas"), (
        f"Expected 'Campinas' in results: {city_names}"
    )


def test_search_uberlandia_returns_uberlandia(suggestions):
    """Searching 'uber' should return Uberlândia."""
    results = suggestions.search_cities("uber", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Uberlândia"), (
        f"Expected 'Uberlândia' in results: {city_names}"
    )


def test_search_natal_returns_natal(suggestions):
    """Searching 'natal' should return Natal."""
    results = suggestions.search_cities("natal", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Natal"), (
        f"Expected 'Natal' in results: {city_names}"
    )


def test_search_maceio_returns_maceio(suggestions):
    """Searching 'mace' should return Maceió."""
    results = suggestions.search_cities("mace", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Maceió"), (
        f"Expected 'Maceió' in results: {city_names}"
    )


def test_search_salvador_returns_salvador(suggestions):
    """Searching 'salv' should return Salvador."""
    results = suggestions.search_cities("salv", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Salvador"), (
        f"Expected 'Salvador' in results: {city_names}"
    )


def test_search_brasilia_returns_brasilia(suggestions):
    """Searching 'brasilia' should return Brasília."""
    results = suggestions.search_cities("brasilia", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Brasília"), (
        f"Expected 'Brasília' in results: {city_names}"
    )


def test_search_manaus_returns_manaus(suggestions):
    """Searching 'manaus' should return Manaus."""
    results = suggestions.search_cities("manaus", limit=5)
    assert len(results) > 0
    city_names = [r.city_name for r in results]
    assert contains_normalized(city_names, "Manaus"), (
        f"Expected 'Manaus' in results: {city_names}"
    )


def test_search_results_have_valid_state_codes(suggestions):
    """All results should have valid Brazilian state codes."""
    results = suggestions.search_cities("rio de", limit=10)
    valid_states = {
        "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS", "MG",
        "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC", "SP", "SE", "TO"
    }
    for r in results:
        assert r.state_code in valid_states, f"Invalid state code: {r.state_code}"


def test_search_results_have_valid_coordinates(suggestions):
    """All results should have valid Brazil coordinates."""
    results = suggestions.search_cities("sao paulo", limit=5)
    for r in results:
        # Brazil lat: -33 to 5, lon: -73 to -34
        assert -35 <= r.latitude <= 5, f"Invalid latitude: {r.latitude}"
        assert -75 <= r.longitude <= -32, f"Invalid longitude: {r.longitude}"


def test_search_limit_respected(suggestions):
    """Search limit should be respected."""
    results = suggestions.search_cities("sao paulo", limit=3)
    assert len(results) <= 3


def test_search_empty_returns_empty(suggestions):
    """Empty query returns empty list."""
    results = suggestions.search_cities("", limit=10)
    assert results == []


def test_search_returns_cityinfo_objects(suggestions):
    """Results should be CityInfo objects with all fields."""
    results = suggestions.search_cities("rio de", limit=5)
    assert all(isinstance(r, CityInfo) for r in results)
    for r in results:
        assert r.city_code > 0
        assert r.city_name
        assert r.city_normalized
        assert r.state_code
        assert r.latitude != 0 or r.longitude != 0  # coordinates available