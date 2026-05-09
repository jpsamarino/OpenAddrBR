"""
Tests for get_city_code using IBGEGeocoder.
"""

import pytest

from application import IBGEGeocoder


@pytest.fixture
def coder():
    """Coder instance for testing."""
    return IBGEGeocoder()


class TestGetCityCode:
    """Tests for get_city_info."""

    def test_sao_paulo(self, coder):
        """Testa busca por São Paulo."""
        result = coder.get_city_info("São Paulo", "SP")
        assert result is not None
        assert result.city_code == 3550308

    def test_rio_de_janeiro(self, coder):
        """Testa busca por Rio de Janeiro."""
        result = coder.get_city_info("Rio de Janeiro", "RJ")
        assert result is not None
        assert result.city_code == 3304557

    def test_belo_horizonte(self, coder):
        """Testa busca por Belo Horizonte."""
        result = coder.get_city_info("Belo Horizonte", "MG")
        assert result is not None
        assert result.city_code == 3106200

    def test_curitiba(self, coder):
        """Testa busca por Curitiba."""
        result = coder.get_city_info("Curitiba", "PR")
        assert result is not None
        assert result.city_code == 4106902

    def test_sao_jose_dos_campos(self, coder):
        """Testa busca por São José dos Campos."""
        result = coder.get_city_info("São José dos Campos", "SP")
        assert result is not None
        assert result.city_code == 3549904

    def test_nome_com_acento(self, coder):
        """Testa que acentos são normalizados corretamente."""
        result = coder.get_city_info("Sao Paulo", "SP")
        assert result is not None
        assert result.city_code == 3550308

    def test_estado_minusculo(self, coder):
        """Testa que estado em minúsculo funciona."""
        result = coder.get_city_info("São Paulo", "sp")
        assert result is not None
        assert result.city_code == 3550308

    def test_estado_maiusculo(self, coder):
        """Testa que estado em maiúsculo funciona."""
        result = coder.get_city_info("São Paulo", "SP")
        assert result is not None
        assert result.city_code == 3550308

    def test_municipio_nao_encontrado(self, coder):
        """Testa retorno para município inexistente."""
        result = coder.get_city_info("Cidade Inexistente XYZ", "XX")
        assert result is None

    def test_municipio_vazio(self, coder):
        """Testa retorno para município vazio."""
        result = coder.get_city_info("", "SP")
        assert result is None
