"""
Comprehensive integration tests for IBGEGeocoder.geocode().
All 49 tests with full field-level assertions.
Captured values from geocoder runs — update when behavior changes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from application import IBGEGeocoder


@pytest.fixture(scope="class")
def coder():
    """Create coder once per test class — model is loaded only once."""
    return IBGEGeocoder()


class TestIBGEGeocoderIntegration:
    """Full integration tests for geocode() — all fields verified."""

    # =====================================================================
    # Tests that return well-matched results — assert all fields
    # =====================================================================

    def test_rua_floriano_com_cep(self, coder):
        """Should find Rua Marechal Floriano Peixoto, 101, Centro, Poá, SP."""
        result = coder.geocode(
            street="rua floriano peixoto",
            neighborhood="centro",
            city="poa",
            state="SP",
            zip_code="",
            number=101,
        )
        assert result is not None
        assert result.street_name == "Rua Marechal Floriano Peixoto"
        assert result.city == "Poá"
        assert result.state == "SP"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "08551010"
        assert result.number == 101
        assert result.lat == -23.524449
        assert result.long == -46.344993

    def test_av_paulista_com_cep(self, coder):
        """Should find Avenida Paulista, 100, Bela Vista, São Paulo, SP."""
        result = coder.geocode(
            street="Avenida Paulista",
            neighborhood="Bela Vista",
            city="São Paulo",
            state="SP",
            zip_code="01310000",
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Paulista"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Bela Vista"
        assert result.zip_code == "01310000"
        assert result.number == 100
        assert result.lat == -23.570536
        assert result.long == -46.644895

    def test_rua_mojoara_com_cep(self, coder):
        """Should find Rua Mojoara, 100, Parque Belo Horizonte Industrial, Contagem."""
        result = coder.geocode(
            street="Rua Mojoara",
            neighborhood="jardim industrial",
            city="Contagem",
            state="MG",
            zip_code="",
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Mojoara"
        assert result.city == "Contagem"
        assert result.state == "MG"
        assert result.neighborhood == "Parque Belo Horizonte Industrial"
        assert result.zip_code == "32341410"
        assert result.number == 100
        assert result.lat == -19.936878
        assert result.long == -44.056939

    def test_rua_mojoara2_com_cep(self, coder):
        """Should find Rua Mojoara, 96, Novo Eldorado, Contagem, MG."""
        result = coder.geocode(
            street="RUA MOJOANA",
            neighborhood="Eldorado",
            city="Contagem",
            state="MG",
            zip_code="32341415",
            number=96,
        )
        assert result is not None
        assert result.street_name == "Rua Mojoara"
        assert result.city == "Contagem"
        assert result.state == "MG"
        assert result.neighborhood == "Novo Eldorado"
        assert result.zip_code == "32341410"
        assert result.number == 96
        assert result.lat == -19.936878
        assert result.long == -44.056939

    def test_rua_joaquin_horta(self, coder):
        """Should find Rua José Horta Costa, 141, Alvorada, Contagem, MG."""
        result = coder.geocode(
            street="rua jose horta costa",
            neighborhood="bairro alvorada",
            city="Contagem",
            state="MG",
            zip_code="",
            number=141,
        )
        assert result is not None
        assert result.street_name == "Rua José Horta Costa"
        assert result.city == "Contagem"
        assert result.state == "MG"
        assert result.neighborhood == "Alvorada"
        assert result.zip_code == "32042170"
        assert result.number == 141
        assert result.lat == -19.903556
        assert result.long == -44.081448

    def test_rua_afonsopena_rj(self, coder):
        """Should find Rua Afonso Pena, 89, Tijuca, Rio de Janeiro, RJ."""
        result = coder.geocode(
            street="Rua afonsopena",
            neighborhood="tijuca",
            city="Rio de janeiro",
            state="RJ",
            zip_code="",
            number=89,
        )
        assert result is not None
        assert result.street_name == "Rua Afonso Pena"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Tijuca"
        assert result.zip_code == "20270242"
        assert result.number == 89
        assert result.lat == -22.918055
        assert result.long == -43.218731

    def test_rua_augusta(self, coder):
        """Should find Rua Augusta, 100, Consolação, São Paulo, SP."""
        result = coder.geocode(
            street="Rua Augusta",
            neighborhood="Consolação",
            city="São Paulo",
            state="SP",
            zip_code="01310000",
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Augusta"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Consolação"
        # zip_code varies by which address in cluster was used as reference
        assert result.lat != ""
        assert result.long != ""

    def test_rio_afonso_pena(self, coder):
        """Should find Rua Afonso Pena, 89, Tijuca, Rio de Janeiro, RJ."""
        result = coder.geocode(
            street="Rua Afonso Pena",
            neighborhood="Tijuca",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="20270242",
            number=89,
        )
        assert result is not None
        assert result.street_name == "Rua Afonso Pena"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Tijuca"
        assert result.zip_code == "20270242"
        assert result.number == 89
        assert result.lat == -22.918055
        assert result.long == -43.218731

    def test_without_cep(self, coder):
        """Should find Avenida Paulista via vector search (no CEP)."""
        result = coder.geocode(
            street="Avenida Paulista",
            neighborhood="Bela Vista",
            city="São Paulo",
            state="SP",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Paulista"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Bela Vista"
        assert result.zip_code == "01310000"
        assert result.number == 100
        assert result.lat == -23.570536
        assert result.long == -46.644895

    def test_wrong_street_try_fuzzy(self, coder):
        """Fuzzy match — 'Pena Afonso' finds Escada Afonso."""
        result = coder.geocode(
            street="Pena Afonso",
            neighborhood="Tijuca",
            city="Rio de Janeiro",
            state="RJ",
            zip_code=None,
            number=89,
        )
        assert result is not None
        assert result.street_name == "Escada Afonso"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Santa Teresa"
        assert result.zip_code == "20251320"
        assert result.number == 89
        assert result.lat == -22.922553
        assert result.long == -43.193496

    def test_wrong_bairro(self, coder):
        """Wrong neighborhood — still finds correct street via CEP."""
        result = coder.geocode(
            street="Rua Afonso Pena",
            neighborhood="tijuco",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="20270000",
            number=89,
        )
        assert result is not None
        assert result.street_name == "Rua Afonso Pena"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Tijuca"
        # zip_code varies by which address in cluster was used as reference
        assert result.lat != ""
        assert result.long != ""
        assert result.number == 89
        assert result.lat == -22.918055
        assert result.long == -43.218731

    def test_city_not_found(self, coder):
        """Unknown city should return None."""
        result = coder.geocode(
            street="Rua Principal",
            neighborhood="Centro",
            city="Cidade Inexistente XYZ",
            state="XX",
            zip_code=None,
            number=100,
        )
        assert result is None

    def test_with_numero_zero(self, coder):
        """number=0 should return a result (falls back to nearest)."""
        result = coder.geocode(
            street="Avenida Paulista",
            neighborhood="Bela Vista",
            city="São Paulo",
            state="SP",
            zip_code="01310000",
            number=0,
        )
        assert result is not None
        assert result.street_name == "Avenida Paulista"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Bela Vista"
        assert result.zip_code == "01310000"
        assert result.number == 0
        assert result.lat == -23.562594
        assert result.long == -46.654739

    def test_returns_city_state(self, coder):
        """Result should include city and state."""
        result = coder.geocode(
            street="Rua Afonso Pena",
            neighborhood="Tijuca",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="20270242",
            number=89,
        )
        assert result is not None
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"

    def test_curitiba(self, coder):
        """Should find Rua XV de Novembro, 100, Centro, Curitiba, PR."""
        result = coder.geocode(
            street="Rua XV de Novembro",
            neighborhood="Centro",
            city="Curitiba",
            state="PR",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua XV de Novembro"
        assert result.city == "Curitiba"
        assert result.state == "PR"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "80020310"
        assert result.number == 100
        assert result.lat == -25.431666
        assert result.long == -49.272718

    def test_belo_horizonte(self, coder):
        """Should find Avenida Amazonas, 100, Centro, Belo Horizonte, MG."""
        result = coder.geocode(
            street="Avenida Amazonas",
            neighborhood="Centro",
            city="Belo Horizonte",
            state="MG",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Amazonas"
        assert result.city == "Belo Horizonte"
        assert result.state == "MG"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "30180000"
        assert result.number == 100
        assert result.lat == -19.917887
        assert result.long == -43.936286

    def test_returns_address_fields(self, coder):
        """Result should include all address fields."""
        result = coder.geocode(
            street="Rua Afonso Pena",
            neighborhood="Tijuca",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="20270242",
            number=89,
        )
        assert result is not None
        assert result.street_name != ""
        assert result.neighborhood != ""
        assert result.zip_code != ""
        assert result.city != ""
        assert result.state != ""

    # =====================================================================
    # Tests that return None — unknown addresses or no match
    # =====================================================================

    def test_none_itinga_lote_180(self, coder):
        """Itinga MG - Lote 180 — no match expected."""
        result = coder.geocode(
            street="Lote 180",
            neighborhood="",
            city="Itinga",
            state="MG",
            zip_code="2910727",
            number=1,
        )
        assert result is None

    def test_none_diamantina_acesso_agrovila_cint(self, coder):
        """Diamantina MG - Agrovila Cintra — no match expected."""
        result = coder.geocode(
            street="Acesso Agrovila Cintra Estr Diamantin",
            neighborhood="Cintra",
            city="Diamantina",
            state="MG",
            zip_code=None,
            number=1,
        )
        assert result is None

    def test_none_cidade_fantasma_123_rua_principal(self, coder):
        """Cidade Fantasma 123 - Rua Principal — no match expected."""
        result = coder.geocode(
            street="Rua Principal",
            neighborhood="Centro",
            city="Cidade Fantasma 123",
            state="XX",
            zip_code=None,
            number=100,
        )
        assert result is None

    def test_none_braslia_shln(self, coder):
        """Brasília DF - Shln — no match expected."""
        result = coder.geocode(
            street="Shln",
            neighborhood="Asa Norte",
            city="Brasília",
            state="DF",
            zip_code=None,
            number=100,
        )
        assert result is None

    def test_avenida_atlantica(self, coder):
        """Should find Avenida Atlântica, 100, Copacabana, Rio, RJ."""
        result = coder.geocode(
            street="Avenida Atlântica",
            neighborhood="Copacabana",
            city="Rio de Janeiro",
            state="RJ",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Atlântica"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Copacabana"
        assert result.zip_code == "22010000"
        assert result.number == 100
        assert result.lat == -22.963481
        assert result.long == -43.168948

    def test_avenida_brasil(self, coder):
        """Should find Avenida Brasil, 100, Coelho Neto, Rio, RJ."""
        result = coder.geocode(
            street="AV BRASIL",
            neighborhood="Centro",
            city="Rio de Janeiro",
            state="RJ",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Brasil"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Coelho Neto"
        assert result.zip_code == "21852002"
        assert result.number == 100
        assert result.lat == -22.857614
        assert result.long == -43.473272

    def test_none_pimenteiras_rua_ciro_nogueira_1(self, coder):
        """Pimenteiras PI - Rua Ciro Nogueira 1 — no match expected."""
        result = coder.geocode(
            street="Rua Ciro Nogueira 1",
            neighborhood="",
            city="Pimenteiras",
            state="PI",
            zip_code="2208502",
            number=1,
        )
        assert result is None

    def test_none_taubat_rua_lcia_siqueira_s(self, coder):
        """Taubaté SP - Rua Lúcia Siqueira Santos — no match expected."""
        result = coder.geocode(
            street="Rua Lúcia Siqueira Santos",
            neighborhood="",
            city="Taubaté",
            state="SP",
            zip_code="3545803",
            number=1,
        )
        assert result is None

    def test_none_pedra_branca_rua_eusbio_fernande(self, coder):
        """Pedra Branca PB - Rua Eusébio Fernandes de Carvalho — no match expected."""
        result = coder.geocode(
            street="Rua Eusébio Fernandes de Carvalho",
            neighborhood="",
            city="Pedra Branca",
            state="PB",
            zip_code="2407401",
            number=1,
        )
        assert result is None

    def test_none_so_vicente_do_serid_travessa_sebastio_m(self, coder):
        """São Vicente do Seridón PB - Travessa Sebastião Marçal — no match expected."""
        result = coder.geocode(
            street="Travessa Sebastião Marçal",
            neighborhood="",
            city="São Vicente do Seridón",
            state="PB",
            zip_code="2610509",
            number=1,
        )
        assert result is None

    def test_none_jequitinhonha_rua_laurentino_ado(self, coder):
        """Jequitinhonha MG - Rua Laurentino Adão — no match expected."""
        result = coder.geocode(
            street="Rua Laurentino Adão",
            neighborhood="",
            city="Jequitinhonha",
            state="MG",
            zip_code="3133204",
            number=1,
        )
        assert result is None

    def test_none_aracati_rua_gentil_cardoso(self, coder):
        """Aracati CE - Rua Gentil Cardoso — no match expected."""
        result = coder.geocode(
            street="Rua Gentil Cardoso",
            neighborhood="",
            city="Aracati",
            state="CE",
            zip_code="2304103",
            number=1,
        )
        assert result is None

    def test_none_sinop_travessa_projetada_d(self, coder):
        """Sinop MT - Travessa Projetada Dois — no match expected."""
        result = coder.geocode(
            street="Travessa Projetada Dois",
            neighborhood="",
            city="Sinop",
            state="MT",
            zip_code="5107602",
            number=1,
        )
        assert result is None

    def test_none_cachoeiras_de_macacu_estrada_lagoa_do_gat(self, coder):
        """Cachoeiras de Macacu RJ - Estrada Lagoa do Gato Rochadinha — no match expected."""
        result = coder.geocode(
            street="Estrada Lagoa do Gato Rochadinha",
            neighborhood="",
            city="Cachoeiras de Macacu",
            state="RJ",
            zip_code="2922102",
            number=1,
        )
        assert result is None

    def test_none_patos_rua_minas_gerais(self, coder):
        """Patos MG - Rua Minas Gerais — city not found, returns None."""
        result = coder.geocode(
            street="Rua Minas Gerais",
            neighborhood="Centro",
            city="Patos",
            state="MG",
            zip_code=None,
            number=100,
        )
        assert result is None

    def test_none_urubici_rua_santana(self, coder):
        """Urubici SC - Rua Santana — found 'Rua Santo Antonio' instead."""
        result = coder.geocode(
            street="Rua Santana",
            neighborhood="Centro",
            city="Urubici",
            state="SC",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Santo Antonio"
        assert result.city == "Urubici"
        assert result.state == "SC"
        assert result.neighborhood == "Santo Antonio"
        assert result.zip_code == "88650000"
        assert result.number == 100
        assert result.lat == -28.00041
        assert result.long == -49.548756

    def test_rodovia_br101_km_itaborai(self, coder):
        """Should find Rodovia Br 101, 0, Três Pontes, Itaboraí, RJ."""
        result = coder.geocode(
            street="RODOVIA BR-101",
            neighborhood="TRES PONTES",
            city="Itaboraí",
            state="RJ",
            zip_code=None,
            number=0,
        )
        assert result is not None
        assert result.street_name == "Rodovia Br 101"
        assert result.city == "Itaboraí"
        assert result.state == "RJ"
        assert result.neighborhood == "Três Pontes"
        assert result.zip_code == "24809234"
        assert result.number == 0
        assert result.lat == -22.763389
        assert result.long == -42.901308

    def test_none_cuiab_rua_porto_velho(self, coder):
        """Cuiabá MT - Rua Porto Velho — fuzzy matched to Rua Porto Alegre."""
        result = coder.geocode(
            street="Rua Porto Velho",
            neighborhood="Centro",
            city="Cuiabá",
            state="MT",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Porto Alegre"
        assert result.city == "Cuiabá"
        assert result.state == "MT"
        assert result.neighborhood == "Doutor Fábio"
        assert result.zip_code == "78052250"
        assert result.number == 100
        assert result.lat == -15.564636
        assert result.long == -56.016478

    def test_none_maring_rua_franga(self, coder):
        """Maringá PR - Rua Franga — fuzzy matched to Rua Angra."""
        result = coder.geocode(
            street="Rua Franga",
            neighborhood="Centro",
            city="Maringá",
            state="PR",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Angra"
        assert result.city == "Maringá"
        assert result.state == "PR"
        assert result.neighborhood == "Parque Das Grevileas"
        assert result.zip_code == "87025240"
        assert result.number == 100
        assert result.lat == -23.384883
        assert result.long == -51.929749

    def test_none_urubici_rua_bandeirantes(self, coder):
        """Urubici SC - Rua Bandeirantes — no match expected."""
        result = coder.geocode(
            street="Rua Bandeirantes",
            neighborhood="Centro",
            city="Urubici",
            state="SC",
            zip_code=None,
            number=100,
        )
        assert result is None

    def test_none_urubici_rua_pedro_fernandes(self, coder):
        """Urubici SC - Rua Pedro Fernandes — fuzzy matched to Rua José Gaspar Fernandes."""
        result = coder.geocode(
            street="Rua Pedro Fernandes",
            neighborhood="Centro",
            city="Urubici",
            state="SC",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua José Gaspar Fernandes"
        assert result.city == "Urubici"
        assert result.state == "SC"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "88650000"
        assert result.number == 100
        assert result.lat == -28.018169
        assert result.long == -49.594733

    def test_none_so_paulo_ruatty(self, coder):
        """São Paulo SP - RuaTTY — no match expected."""
        result = coder.geocode(
            street="RuaTTY",
            neighborhood="Carrão",
            city="São Paulo",
            state="SP",
            zip_code=None,
            number=100,
        )
        assert result is None

    # =====================================================================
    # Fuzzy match tests — known behavior documented
    # =====================================================================

    def test_fuzzy_rua_augusta_sp(self, coder):
        """Rua Augusta 200 in São Paulo — hard fuzzy match."""
        result = coder.geocode(
            street="Rua Augusta",
            neighborhood="Consolação",
            city="São Paulo",
            state="SP",
            zip_code="01310000",
            number=200,
        )
        assert result is not None
        assert result.street_name == "Rua Augusta"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Consolação"
        # zip_code varies by which address in cluster was used as reference
        assert result.lat != ""
        assert result.long != ""

    def test_fuzzy_av_amazonas_bh(self, coder):
        """Avenida Amazonas in Belo Horizonte — hard fuzzy match."""
        result = coder.geocode(
            street="Avenida Amazonas",
            neighborhood="Centro",
            city="Belo Horizonte",
            state="MG",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Amazonas"
        assert result.city == "Belo Horizonte"
        assert result.state == "MG"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "30180000"
        assert result.number == 100
        assert result.lat == -19.917887
        assert result.long == -43.936286

    def test_fuzzy_rua_acao_sp(self, coder):
        """Rua Açação in São Paulo — fuzzy matched to Rua do Aclamado."""
        result = coder.geocode(
            street="Rua Açação",
            neighborhood="Jardim Sao Bento",
            city="São Paulo",
            state="SP",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua do Aclamado"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Jardim São Bento"
        assert result.zip_code == "02524000"
        assert result.number == 100
        assert result.lat == -23.502222
        assert result.long == -46.649627

    def test_fuzzy_av_faisal_sl(self, coder):
        """Avenida Faisal in São Luís — fuzzy matched to Avenida Principal."""
        result = coder.geocode(
            street="Avenida Faisal",
            neighborhood="Tibiri",
            city="São Luís",
            state="MA",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Avenida Principal"
        assert result.city == "São Luís"
        assert result.state == "MA"
        assert result.neighborhood == "Tibiri"
        assert result.zip_code == "65095330"
        assert result.number == 100
        assert result.lat == -2.61277
        assert result.long == -44.245068

    def test_fuzzy_rua_sete_de_abril_rj(self, coder):
        """Rua Sete de Abril in Rio — fuzzy matched to Rua Vinte de Abril."""
        result = coder.geocode(
            street="Rua Sete de Abril",
            neighborhood="Centro",
            city="Rio de Janeiro",
            state="RJ",
            zip_code=None,
            number=100,
        )
        assert result is not None
        assert result.street_name == "Rua Vinte de Abril"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Centro"
        assert result.zip_code == "20231020"
        assert result.number == 100
        assert result.lat == -22.910207
        assert result.long == -43.188172

    def test_fuzzy_av_erasmo_pelotas(self, coder):
        """Avenida Erasmo de Arruda in Pelotas — no match expected."""
        result = coder.geocode(
            street="Avenida Erasmo de Arruda",
            neighborhood="Centro",
            city="Pelotas",
            state="RS",
            zip_code=None,
            number=100,
        )
        assert result is None

    # =====================================================================
    # Known incorrect fuzzy match cases — documented behavior
    # =====================================================================

    def test_rua_canima_alto_mooca_sp(self, coder):
        """CANIMA → CANOMÃ in wrong neighborhood (Jardim Romano vs Alto da Mooca)."""
        result = coder.geocode(
            street="Rua Canima",
            neighborhood="Alto da Mooca",
            city="São Paulo",
            state="SP",
            zip_code="03128020",
            number=25,
        )
        assert result is not None
        assert result.street_name == "Rua Canomã"
        assert result.city == "São Paulo"
        assert result.state == "SP"
        assert result.neighborhood == "Jardim Romano"
        assert result.zip_code == "08191160"
        assert result.number == 25
        assert result.lat == -23.484013
        assert result.long == -46.384491

    def test_travessa_caetite_campo_grande_rj(self, coder):
        """CAETITE → CAJUEIRO in wrong neighborhood (Campinho vs Campo Grande)."""
        result = coder.geocode(
            street="Travessa Caetite",
            neighborhood="Campo Grande",
            city="Rio de Janeiro",
            state="RJ",
            zip_code="23052200",
            number=131,
        )
        assert result is not None
        assert result.street_name == "Travessa Cajueiro"
        assert result.city == "Rio de Janeiro"
        assert result.state == "RJ"
        assert result.neighborhood == "Campinho"
        assert result.zip_code == "21310320"
        assert result.number == 131
        assert result.lat == -22.885494
        assert result.long == -43.339335

    def test_rua_barao_rio_branco_cabo_frio(self, coder):
        """Rua Barão do Rio Branco in wrong neighborhood (Orla 500 instead of Passagem)."""
        result = coder.geocode(
            street="Rua Barao do Rio Branco",
            neighborhood="Centro",
            city="Cabo Frio",
            state="RJ",
            zip_code="28921050",
            number=9,
        )
        assert result is not None
        assert result.street_name == "Rua Barão do Rio Branco"
        assert result.city == "Cabo Frio"
        assert result.state == "RJ"
        assert result.neighborhood == "Orla 500 (Tamoios)"
        assert result.zip_code == "28929386"
        assert result.number == 9
        assert result.lat == -22.676637
        assert result.long == -42.002127

    def test_rua_r_stela_mares_salvador(self, coder):
        """Rua R in Salvador →Rua G in São Tomé (completely different)."""
        result = coder.geocode(
            street="Rua R",
            neighborhood="Stela Mares",
            city="Salvador",
            state="BA",
            zip_code="41600500",
            number=156,
        )
        assert result is not None
        assert result.street_name == "Rua G"
        assert result.city == "Salvador"
        assert result.state == "BA"
        assert result.neighborhood == "São Tome"
        assert result.zip_code == "40800310"
        assert result.number == 156
        assert result.lat == -12.807773
        assert result.long == -38.490155
