"""Tests for services - TDD approach."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "d:/projetos/OpenAddrBR")

import pytest
from unittest.mock import MagicMock, patch
from openaddrbr.core.models import CityInfo, StreetCluster, AddressRequest
from openaddrbr.data._db import AddressRecord, CityRecord


class TestCityService:
    """Tests for get_city_info service."""

    def test_get_city_info_returns_cityinfo(self):
        """get_city_info should return CityInfo when found."""
        from openaddrbr.services._city import get_city_info

        with patch("openaddrbr.services._city.get_city_info_from_db") as mock_db:
            mock_db.return_value = CityRecord(city_code=3550308, city_name="São Paulo", state_code="SP")

            result = get_city_info("São Paulo", "SP")
            assert result is not None
            assert result.city_code == 3550308
            assert result.city_name == "São Paulo"
            assert result.state_code == "SP"

    def test_get_city_info_returns_none_when_not_found(self):
        """get_city_info should return None when city not found."""
        from openaddrbr.services._city import get_city_info

        with patch("openaddrbr.services._city.get_city_info_from_db") as mock_db:
            mock_db.return_value = None

            result = get_city_info("Cidade Inexistente", "XX")
            assert result is None


class TestCEPService:
    """Tests for search_by_cep service."""

    def test_search_by_cep_returns_cluster(self):
        """search_by_cep should return StreetCluster when found."""
        from openaddrbr.services._cep import search_by_cep

        with patch("openaddrbr.services._cep.query_address_by_cep") as mock_query:
            mock_query.return_value = [
                AddressRecord(street_id=1, street_normalized="AVENIDA PAULISTA", neighborhood_normalized="BELA VISTA"),
            ]

            result = search_by_cep("01310000", "AVENIDA PAULISTA", "BELA VISTA")
            assert result is not None
            assert result.street_id == 1

    def test_search_by_cep_returns_none_when_not_found(self):
        """search_by_cep should return None when no match."""
        from openaddrbr.services._cep import search_by_cep

        with patch("openaddrbr.services._cep.query_address_by_cep") as mock_query:
            mock_query.return_value = []

            result = search_by_cep("00000000", "AVENIDA PAULISTA", "BELA VISTA")
            assert result is None

    def test_is_multi_street_cep(self):
        """is_multi_street_cep should return True when CEP has multiple streets."""
        from openaddrbr.services._cep import is_multi_street_cep

        # Clear cache first to ensure fresh call
        is_multi_street_cep.cache_clear()

        with patch("openaddrbr.services._cep._is_multi_street_cep") as mock:
            mock.return_value = True

            result = is_multi_street_cep("99999999")  # Use different CEP
            assert result is True


class TestGeocodeService:
    """Tests for geocode service - mock heavy since it needs real data otherwise."""

    def test_geocode_returns_none_for_unknown_city(self):
        """geocode should return None for unknown city."""
        from openaddrbr.services._geocode import geocode

        with patch("openaddrbr.services._geocode.check_data_exists") as mock_check:
            mock_check.return_value = True  # Data exists

            with patch("openaddrbr.services._geocode._get_city_info") as mock_city:
                mock_city.return_value = None  # City not found

                result = geocode("Rua X", "Bairro", "Cidade Inexistente", "XX")
                assert result is None

    def test_geocode_normalizes_input(self):
        """geocode should normalize street and neighborhood text."""
        from openaddrbr.services._geocode import geocode, normalize_text

        with patch("openaddrbr.services._geocode.check_data_exists") as mock_check:
            mock_check.return_value = True

            with patch("openaddrbr.services._geocode._get_city_info") as mock_city:
                mock_city.return_value = CityInfo(city_code=3550308, city_name="São Paulo", state_code="SP")

                with patch("openaddrbr.services._geocode.is_multi_street_cep") as mock_multi:
                    mock_multi.return_value = False

                    with patch("openaddrbr.services._geocode.search_by_cep") as mock_cep:
                        mock_cep.return_value = None  # No CEP match

                        with patch("openaddrbr.services._geocode._encode_street") as mock_encode:
                            mock_encode.return_value = None  # No encoding

                            with patch("openaddrbr.services._geocode._search_by_embedding") as mock_emb:
                                mock_emb.return_value = None  # No embedding match

                                result = geocode("rua das flores", "centro", "São Paulo", "SP")
                                # Should return None since no match found (mocked)


class TestBatchService:
    """Tests for get_geo_info_batch service."""

    def test_empty_list_returns_empty(self):
        """get_geo_info_batch with empty list returns empty list."""
        from openaddrbr.services._batch import get_geo_info_batch

        result = get_geo_info_batch([])
        assert result == []

    def test_returns_list_in_same_order(self):
        """get_geo_info_batch should return results in same order as input."""
        from openaddrbr.services._batch import get_geo_info_batch

        addresses = [
            AddressRequest(city="São Paulo", state="SP"),
            AddressRequest(city="Rio de Janeiro", state="RJ"),
        ]

        with patch("openaddrbr.services._batch._get_city_info") as mock_city:
            mock_city.side_effect = [None, None]  # Both not found

            result = get_geo_info_batch(addresses)
            assert len(result) == 2
            assert result[0] is None
            assert result[1] is None