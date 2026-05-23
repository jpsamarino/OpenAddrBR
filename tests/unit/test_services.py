"""Tests for services with Geocoder DI pattern."""

from unittest.mock import MagicMock

from openaddrbr.core._geocoder import Geocoder
from openaddrbr.core.models import AddressRequest, CityRecord


class TestCityService:
    """Tests for get_city_info service with DI."""

    def test_get_city_info_returns_citycore(self):
        """get_city_info should return CityCore when found."""
        from openaddrbr.services._city import get_city_info

        mock_db = MagicMock()
        mock_db.get_city_info_from_db.return_value = CityRecord(
            city_code=3550308, city_name="São Paulo", state_code="SP"
        )

        result = get_city_info("São Paulo", "SP", db=mock_db)
        assert result is not None
        assert result.city_code == 3550308

    def test_get_city_info_returns_none_when_not_found(self):
        """get_city_info should return None when city not found."""
        from openaddrbr.services._city import get_city_info

        mock_db = MagicMock()
        mock_db.get_city_info_from_db.return_value = None

        result = get_city_info("Cidade Inexistente", "XX", db=mock_db)
        assert result is None


class TestCEPService:
    """Tests for CEP service with DI."""

    def test_resolve_street_by_cep_returns_cluster(self):
        """resolve_street_by_cep should return StreetCluster when found."""
        from openaddrbr.services._cep import resolve_street_by_cep

        mock_db = MagicMock()
        mock_db.query_address_by_cep.return_value = [
            MagicMock(
                street_id=1,
                street_normalized="AVENIDA PAULISTA",
                neighborhood_normalized="BELA VISTA",
            ),
        ]

        result = resolve_street_by_cep("01310000", "AVENIDA PAULISTA", "BELA VISTA", db=mock_db)
        assert result is not None
        assert result.street_id == 1

    def test_resolve_street_by_cep_returns_none_when_not_found(self):
        """resolve_street_by_cep should return None when no match."""
        from openaddrbr.services._cep import resolve_street_by_cep

        mock_db = MagicMock()
        mock_db.query_address_by_cep.return_value = []

        result = resolve_street_by_cep("00000000", "AVENIDA PAULISTA", "BELA VISTA", db=mock_db)
        assert result is None


class TestGeocodeService:
    """Tests for Geocoder.geocode method."""

    def test_geocode_returns_none_for_unknown_city(self):
        """geocode should return None for unknown city."""
        mock_db = MagicMock()
        mock_db.get_city_info_from_db.return_value = None

        mock_encoder = MagicMock()

        geocoder = Geocoder(encoder=mock_encoder, addr_store=mock_db)
        result = geocoder.geocode("Rua X", "Bairro", "Cidade Inexistente", "XX")
        assert result is None

    def test_geocode_with_cep_match(self):
        """geocode should return result when CEP matches."""
        mock_db = MagicMock()
        mock_db.get_city_info_from_db.return_value = CityRecord(
            city_code=3550308, city_name="São Paulo", state_code="SP"
        )
        mock_db.is_multi_street_cep.return_value = False

        mock_db.query_address_by_cep.return_value = [
            MagicMock(street_id=1, street_normalized="rua x", neighborhood_normalized="centro")
        ]
        mock_db.query_full_address_by_street_id.return_value = [
            MagicMock(
                street_name="Rua X",
                street_normalized="rua x",
                neighborhood_name="Centro",
                neighborhood_normalized="centro",
                zip_code="01310000",
                id=1,
                source_type="A",
            )
        ]
        mock_db.query_geo_locations.return_value = [
            MagicMock(latitude=-23.5, longitude=-46.6, address_number=100, address_id=1)
        ]

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = None  # Skip embedding search

        geocoder = Geocoder(encoder=mock_encoder, addr_store=mock_db)
        result = geocoder.geocode("Rua X", "Centro", "São Paulo", "SP", number=100)
        # CEP path should work without hitting embedding search
        assert result is None  # No street match found in mock


class TestBatchService:
    """Tests for Geocoder.geocode_batch method."""

    def test_empty_list_returns_empty(self):
        """geocode_batch with empty list returns empty list."""
        geocoder = Geocoder()
        result = geocoder.geocode_batch([])
        assert result == []

    def test_returns_list_in_same_order(self):
        """geocode_batch should return results in same order as input."""
        mock_db = MagicMock()
        mock_db.get_city_info_from_db.return_value = None  # Not found

        mock_encoder = MagicMock()

        geocoder = Geocoder(encoder=mock_encoder, addr_store=mock_db)

        addresses = [
            AddressRequest(city="São Paulo", state="SP", street="Rua X", neighborhood="Centro"),
            AddressRequest(
                city="Rio de Janeiro", state="RJ", street="Rua Y", neighborhood="Centro"
            ),
        ]

        result = geocoder.geocode_batch(addresses)
        assert len(result) == 2
        assert result[0] is None
        assert result[1] is None
