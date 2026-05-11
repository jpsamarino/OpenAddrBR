"""Tests for get_city_code using Geocoder."""

import pytest

from openaddrbr import Geocoder


@pytest.fixture
def geocoder():
    """Geocoder instance for testing."""
    return Geocoder()


class TestGetCityCode:
    """Tests for get_city_info via Geocoder.db."""

    def test_sao_paulo(self, geocoder):
        """Testa busca por São Paulo."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("São Paulo", "SP", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3550308

    def test_rio_de_janeiro(self, geocoder):
        """Testa busca por Rio de Janeiro."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("Rio de Janeiro", "RJ", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3304557

    def test_belo_horizonte(self, geocoder):
        """Testa busca por Belo Horizonte."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("Belo Horizonte", "MG", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3106200

    def test_curitiba(self, geocoder):
        """Testa busca por Curitiba."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("Curitiba", "PR", db=geocoder.db)
        assert result is not None
        assert result.city_code == 4106902

    def test_sao_jose_dos_campos(self, geocoder):
        """Testa busca por São José dos Campos."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("São José dos Campos", "SP", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3549904

    def test_nome_com_acento(self, geocoder):
        """Testa que acentos são normalizados corretamente."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("Sao Paulo", "SP", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3550308

    def test_estado_minusculo(self, geocoder):
        """Testa que estado em minúsculo funciona."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("São Paulo", "sp", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3550308

    def test_estado_maiusculo(self, geocoder):
        """Testa que estado em maiúsculo funciona."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("São Paulo", "SP", db=geocoder.db)
        assert result is not None
        assert result.city_code == 3550308

    def test_municipio_nao_encontrado(self, geocoder):
        """Testa retorno para município inexistente."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("Cidade Inexistente XYZ", "XX", db=geocoder.db)
        assert result is None

    def test_municipio_vazio(self, geocoder):
        """Testa retorno para município vazio."""
        from openaddrbr.services._city import get_city_info

        result = get_city_info("", "SP", db=geocoder.db)
        assert result is None
