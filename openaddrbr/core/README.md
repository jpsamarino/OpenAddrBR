# openaddrbr/core — Geocoder & LocationSearch

## 1. Visão Geral

Geocoder + LocationSearch API for Brazilian address geocoding.

- **Geocoder**: address → lat/long coordinates (vector search + IBGE data)
- **LocationSearch**: fast autocomplete for cities, neighborhoods, streets (Tantivy ngram search)

---

## 2. Como Usar

### 2.1 Geocoder

#### geocode()

```python
def geocode(
    self,
    street: str,
    neighborhood: str,
    city: str,
    state: str,
    zip_code: str | None = None,
    number: int = 0,
) -> AddressInfo | None
```

Converte um endereço brasileiro em coordenadas lat/long. Utiliza busca por CEP quando disponível (mais rápida e precisa), e fallback para busca vetorial (embedding) quando CEP não disponível ou é de multi-ruas.

**Exemplo:**

```python
from openaddrbr.core import Geocoder

geocoder = Geocoder()
result = geocoder.geocode(
    street="Rua Marcelina",
    neighborhood="Vila Mariana",
    city="São Paulo",
    state="SP",
    zip_code="04071-080",
    number=142,
)
print(result)
```

**Output:**

```
AddressInfo(lat=-23.5505, long=-46.6333, street_name='Rua Marcelina', neighborhood='Vila Mariana', city='São Paulo', state='SP', zip_code='04071-080', number=142, ref_number_lat_long=0, address='Rua Marcelina, 142, Vila Mariana, São Paulo, SP')
```

#### geocode_batch()

```python
def geocode_batch(
    self,
    addresses: list[AddressRequest],
    batch_size: int | None = None,
) -> list[AddressInfo | None]
```

Geocodifica múltiplos endereços em lote. Agrupa endereços por cidade e rua para otimizar o encoding em batch. Mantém a ordem original dos resultados.

**Exemplo:**

```python
from openaddrbr.core import Geocoder
from openaddrbr.core.models import AddressRequest

geocoder = Geocoder()
addresses = [
    AddressRequest(city="São Paulo", state="SP", street="Rua Marcelina", neighborhood="Vila Mariana", zip_code="04071-080", street_number=142),
    AddressRequest(city="Rio de Janeiro", state="RJ", street="Av Brasil", neighborhood="Centro", zip_code="20010-000", street_number=500),
]
results = geocoder.geocode_batch(addresses)
for r in results:
    print(r)
```

**Output:**

```
AddressInfo(lat=-23.5505, long=-46.6333, street_name='Rua Marcelina', neighborhood='Vila Mariana', city='São Paulo', state='SP', zip_code='04071-080', number=142, ref_number_lat_long=0, address='Rua Marcelina, 142, Vila Mariana, São Paulo, SP')
AddressInfo(lat=-22.9068, long=-43.1729, street_name='Av Brasil', neighborhood='Centro', city='Rio de Janeiro', state='RJ', zip_code='20010-000', number=500, ref_number_lat_long=0, address='Av Brasil, 500, Centro, Rio de Janeiro, RJ')
```

---

### 2.2 LocationSearch

#### search_cities()

```python
def search_cities(self, query: str, limit: int = 10) -> list[CityInfo]
```

Busca cidades por nome usando busca ngram do Tantivy. Retorna até `limit` cidades ordenadas por relevância.

**Exemplo:**

```python
from openaddrbr.core import LocationSearch

search = LocationSearch()
cities = search.search_cities("São Paulo", limit=5)
for c in cities:
    print(c)
```

**Output:**

```
CityInfo(city_code=3550308, city_name='São Paulo', city_normalized='sao paulo', state_code='SP', latitude=-23.5505, longitude=-46.6333)
CityInfo(city_code=3550209, city_name='São Paulo de Piranha', city_normalized='sao paulo de piranha', state_code='AM', latitude=-3.2015, longitude=-64.8085)
CityInfo(city_code=3129806, city_name='São Paulo do Potengi', city_normalized='sao paulo do potengi', state_code='RN', latitude=-6.3782, longitude=-35.4464)
```

#### search_neighborhoods()

```python
def search_neighborhoods(
    self, query: str, city_code: int, limit: int = 10
) -> list[NeighborhoodInfo]
```

Busca bairros por nome dentro de uma cidade específica (filtragem por `city_code` do IBGE). Retorna até `limit` bairros ordenados por relevância.

**Exemplo:**

```python
from openaddrbr.core import LocationSearch

search = LocationSearch()
# São Paulo city_code = 3550308
neighborhoods = search.search_neighborhoods("Vila Mariana", city_code=3550308, limit=5)
for n in neighborhoods:
    print(n)
```

**Output:**

```
NeighborhoodInfo(neighborhood_name='Vila Mariana', neighborhood_normalized='vila mariana', city_code=3550308, latitude=-23.5505, longitude=-46.6333)
NeighborhoodInfo(neighborhood_name='Vila Clementino', neighborhood_normalized='vila clementino', city_code=3550308, latitude=-23.5421, longitude=-46.6181)
```

#### search_streets()

```python
def search_streets(
    self,
    city_code: int,
    query: str,
    neighborhood: str | None = None,
    limit: int = 10,
    autocomplete_query: bool = False,
) -> list[StreetSegmentInfo]
```

Busca ruas por nome dentro de uma cidade específica. Parâmetro `autocomplete_query=True` otimiza para digitação progressiva (prefixo). Parâmetro `neighborhood` aplica boost de similaridade em resultados que correspondem ao bairro informado.

**Exemplo:**

```python
from openaddrbr.core import LocationSearch

search = LocationSearch()
# São Paulo city_code = 3550308
streets = search.search_streets(
    city_code=3550308,
    query="Rua Marcelina",
    neighborhood="Vila Mariana",
    limit=5,
    autocomplete_query=False,
)
for s in streets:
    print(s)
```

**Output:**

```
StreetSegmentInfo(street_id=123456, street_name='Rua Marcelina', street_normalized='rua marcelina', neighborhood_name='Vila Mariana', neighborhood_normalized='vila mariana', zip_codes=['04071-080', '04071-090'], latitude=-23.5505, longitude=-46.6333)
StreetSegmentInfo(street_id=123457, street_name='Rua Marcelina', street_normalized='rua marcelina', neighborhood_name='Vila Clementino', neighborhood_normalized='vila clementino', zip_codes=['04072-100'], latitude=-23.5421, longitude=-46.6181)
```

---

### 2.3 Modelos de Retorno

#### AddressInfo

```python
@dataclass
class AddressInfo:
    lat: float              # Latitude
    long: float             # Longitude
    street_name: str        # Nome da rua
    neighborhood: str       # Nome do bairro
    city: str               # Nome da cidade
    state: str              # Sigla do estado
    zip_code: str           # CEP
    number: int             # Número do endereço
    ref_number_lat_long: int  # Flag se lat/long veio do número
    address: str = ""       # Endereço formatado
```

#### CityInfo

```python
@dataclass
class CityInfo:
    city_code: int          # Código IBGE da cidade
    city_name: str          # Nome da cidade
    city_normalized: str    # Nome normalizado (para busca)
    state_code: str          # Sigla do estado
    latitude: float          # Latitude do centroide
    longitude: float         # Longitude do centroide
```

#### NeighborhoodInfo

```python
@dataclass
class NeighborhoodInfo:
    neighborhood_name: str        # Nome do bairro
    neighborhood_normalized: str  # Nome normalizado
    city_code: int                # Código IBGE da cidade
    latitude: float               # Latitude do centroide
    longitude: float              # Longitude do centroide
```

#### StreetSegmentInfo

```python
@dataclass
class StreetSegmentInfo:
    street_id: int                # ID único da rua
    street_name: str              # Nome da rua
    street_normalized: str        # Nome normalizado
    neighborhood_name: str        # Nome do bairro
    neighborhood_normalized: str  # Bairro normalizado
    zip_codes: list[str]          # Lista de CEPs
    latitude: float               # Latitude do centroide
    longitude: float              # Longitude do centroide
```

---

## 3. Roadmap

| Função | Classe | Status | Descrição |
|--------|--------|--------|-----------|
| geocode | Geocoder | ✅ | Geocodifica endereço para lat/long |
| geocode_batch | Geocoder | ✅ | Geocodifica múltiplos endereços em lote |
| geocode_city | Geocoder | 📋 | Geocodifica apenas pela cidade |
| geocode_neighborhood | Geocoder | 📋 | Geocodifica por bairro |
| geocode_street | Geocoder | 📋 | Geocodifica rua sem número |
| geocode_street_number | Geocoder | 📋 | Geocodifica rua com número específico |
| reverse_geocode | Geocoder | 📋 | given lat/long → address |
| get_addresses_in_radius | Geocoder | 📋 | Lista endereços em raio |
| get_street_numbers | Geocoder | 📋 | Busca números de uma rua |
| search_cities | LocationSearch | ✅ | Busca cidades por nome |
| search_neighborhoods | LocationSearch | ✅ | Busca bairros por nome |
| search_streets | LocationSearch | ✅ | Busca ruas por nome |
| autocomplete_street | LocationSearch | 📋 | Autocomplete de rua |
| autocomplete_addresse | LocationSearch | 📋 | Autocomplete de endereço completo |
| parse_address | LocationSearch | 📋 | Parser de endereço brasileiro |
| search_cep | LocationSearch | 📋 | Busca por CEP |

---

## 4. Performance

### 4.1 Geocoder

| Métrica | Valor |
|---------|-------|
| QPS (queries por segundo) | 43.0 |
| Tempo por query | 23.23ms |
| Acurácia (IBGE result) | 90.7% |
| Endereços <=100m | 55.0% |
| Endereços <=1km | 81.8% |

**O que afeta a performance:**

1. **CEP disponível (mais rápido)**: Quando o CEP é de rua única (`is_multi_street_cep`), a busca usa o CEP diretamente, sem necessidade de vector search.
2. **Fallback vector search**: Quando não há CEP ou é multi-rua, o sistema faz embedding da rua + busca no índice vetorial (usearch). Este é o caminho mais lento.
3. **Batch size**: O `geocode_batch` agrupa endereços por cidade/rua para otimizar o encoding em lote.

### 4.2 LocationSearch

A busca no LocationSearch segue o fluxo: **Tantivy search → SQL lookup → scoring**.

#### search_cities

| Teste | Queries | Avg ms | Acurácia |
|-------|---------|--------|----------|
| Full name | 100 | 2.29 | 100.0% |
| Abbreviation | 100 | 0.10 | 74.0% |
| Partial | 100 | 0.09 | 34.0% |
| First 2 chars | 100 | 0.05 | 8.0% |
| First 3 chars | 100 | 0.07 | 37.0% |

**Overall avg time: 0.52ms | Overall avg accuracy: 50.6%**

#### search_neighborhoods

| Teste | Queries | Avg ms | Acurácia |
|-------|---------|--------|----------|
| Full name | 10000 | 1.7771 | 99.7% |
| Abbreviation | 9999 | 0.7514 | 99.7% |
| Partial | 10000 | 0.5314 | 95.6% |
| First 2 chars | 9984 | 0.0760 | 79.2% |
| First 3 chars | 9984 | 0.2278 | 86.7% |

**Overall avg time: 0.6727ms | Overall avg accuracy: 92.2%**

#### search_streets

| Teste | Normal ms | Auto ms | Speedup | Acc Normal | Acc Auto |
|-------|-----------|---------|---------|------------|---------|
| Full name | 1.5149 | 0.4492 | 3.37x | 100.0% | 98.1% |
| Abbreviation | 1.0251 | 0.3325 | 3.08x | 98.7% | 97.6% |
| Partial | 0.4992 | 0.2477 | 2.02x | 85.7% | 82.9% |
| First 2 chars | 0.3665 | 0.3574 | 1.03x | 10.0% | 10.0% |
| First 3 chars | 0.3921 | 0.3361 | 1.17x | 14.0% | 14.0% |

**Normal mode - Avg time: 0.7596ms, Avg accuracy: 61.7%**
**Auto mode - Avg time: 0.3446ms, Avg accuracy: 60.5%**
**Speedup: 2.20x**

O modo `autocomplete_query=True` é **2.2x mais rápido** que o modo normal, com acurácia similar. Use para digitação progressiva.

**Fluxo completo (Tantivy + SQL + scoring):**

| Etapa | QPS |
|-------|-----|
| Tantivy only | 4260 |
| get_query_id + SQL | 2391 |
| Full flow | 2215 |

### 4.3 Comparativo Geral

| Função | Avg ms | Notas |
|--------|--------|-------|
| search_cities (abbreviation) | 0.10 | Mais rápido |
| search_neighborhoods (first 2 chars) | 0.08 | Muito rápido |
| search_streets (autocomplete) | 0.34 | Boa velocidade |
| search_cities (full name) | 2.29 | Ligeiramente mais lento |
| search_neighborhoods (full name) | 1.78 | Medio |
| geocode (single) | 23.23 | Mais lento (vector search) |

---

## Benchmark Output

### City Autocomplete

```
============================================================
CITY AUTOCOMPLETE BENCHMARK
============================================================

Getting test samples from database...
Loaded 1000 samples

==================================================
Test: Full name
==================================================
Queries tested: 100
Errors: 0
Avg time per query: 2.29ms
Accuracy (expected in top 10): 100.0%

Sample queries:
  OK 'NOVO HORIZONTE DO OESTE' -> expected: NOVO HORIZONTE DO OESTE, first: Novo Horizonte do Oeste, got 10 results in 210.57ms
  OK 'CAMPOS DO JORDAO' -> expected: CAMPOS DO JORDAO, first: Campos do Jordão, got 10 results in 0.0ms
  OK 'AGUAS DE SAO PEDRO' -> expected: AGUAS DE SAO PEDRO, first: Aguas de São Pedro, got 10 results in 1.51ms
  OK 'NAO-ME-TOQUE' -> expected: NAO-ME-TOQUE, first: Não-Me-Toque, got 10 results in 0.0ms
  OK 'RIO NOVO' -> expected: RIO NOVO, first: Rio Novo, got 10 results in 0.0ms

============================================================
SUMMARY
============================================================
Test                 Queries    Avg ms     Accuracy
--------------------------------------------------
Full name            100        2.29       100.0     %
Abbreviation         100        0.10       74.0      %
Partial              100        0.09       34.0      %
First 2 chars        100        0.05       8.0       %
First 3 chars        100        0.07       37.0      %

Overall avg time: 0.52ms
Overall avg accuracy: 50.6%
```

### Neighborhood Autocomplete

```
============================================================
NEIGHBORHOOD AUTOCOMPLETE BENCHMARK
============================================================

Loading benchmark samples...
Loaded 19974 samples from 5570 cities

==================================================
Test: Full name
==================================================
Queries tested: 10000
Errors: 0
Avg time per query: 1.7771ms
Accuracy (expected in top 10): 99.7%

Sample queries:
  OK 'LINHA 144 SUL' -> expected: LINHA 144 SUL, first: Linha 144 Sul, got 10 results in 1145.51ms
  OK 'ALDEIA INDIGENA BOM JESUS 2' -> expected: ALDEIA INDIGENA BOM JESUS 2, first: Aldeia Indígena Bom Jesus 2, got 10 results in 34.4ms
  OK 'ALDEIA INDIGENA BOM SOSSEGO' -> expected: ALDEIA INDIGENA BOM SOSSEGO, first: Aldeia Indígena Bom Sossego, got 10 results in 7.05ms
  OK 'JARDIM PAULISTA' -> expected: JARDIM PAULISTA, first: Jardim Paulista, got 10 results in 7.05ms
  OK 'SOL NASCENTE' -> expected: SOL NASCENTE, first: Sol Nascente, got 10 results in 6.62ms

============================================================
SUMMARY
============================================================
Test                 Queries    Avg ms     Accuracy
--------------------------------------------------
Full name            10000      1.7771     99.7      %
Abbreviation         9999       0.7514     99.7      %
Partial              10000      0.5314     95.6      %
First 2 chars        9984       0.0760     79.2      %
First 3 chars        9984       0.2278     86.7      %

Overall avg time: 0.6727ms
Overall avg accuracy: 92.2%
```

### Street Autocomplete

```
============================================================
COMPARING NORMAL vs AUTOCOMPLETE MODE
============================================================

============================================================
STREET AUTOCOMPLETE BENCHMARK - NORMAL MODE
============================================================

============================================================
SUMMARY
============================================================
Test                 Queries    Avg ms     Accuracy
--------------------------------------------------
Full name            5000       1.5149     100.0     %
Abbreviation         5000       1.0251     98.7      %
Partial              5000       0.4992     85.7      %
First 2 chars        5000       0.3665     10.0      %
First 3 chars        5000       0.3921     14.0      %

Overall avg time: 0.7596ms
Overall avg accuracy: 61.7%

============================================================
STREET AUTOCOMPLETE BENCHMARK - AUTOCOMPLETE MODE
============================================================

============================================================
SUMMARY
============================================================
Test                 Queries    Avg ms     Accuracy
--------------------------------------------------
Full name            5000       0.4492     98.1      %
Abbreviation         5000       0.3325     97.6      %
Partial              5000       0.2477     82.9      %
First 2 chars        5000       0.3574     10.0      %
First 3 chars        5000       0.3361     14.0      %

Overall avg time: 0.3446ms
Overall avg accuracy: 60.5%

============================================================
COMPARISON SUMMARY
============================================================
Test                 Normal ms    Auto ms      Speedup    Acc Normal   Acc Auto
--------------------------------------------------------------------------------
Full name            1.5149       0.4492       3.37      x 100.0       % 98.1      %
Abbreviation         1.0251       0.3325       3.08      x 98.7        % 97.6      %
Partial              0.4992       0.2477       2.02      x 85.7        % 82.9      %
First 2 chars        0.3665       0.3574       1.03      x 10.0        % 10.0      %
First 3 chars        0.3921       0.3361       1.17      x 14.0        % 14.0      %

============================================================
OVERALL COMPARISON
============================================================
Normal mode - Avg time: 0.7596ms, Avg accuracy: 61.7%
Auto mode  - Avg time: 0.3446ms, Avg accuracy: 60.5%
Speedup: 2.20x
```

### Search Streets Full Flow

```
Tantivy street search benchmark - 10000 random queries (autocomplete mode)

Loading 10000 random queries from D:/projetos/SD-External-Data/Scripts-Scraping/Get-Lat-Long/ibge_cnefe_v2/data/sgeobr.db...
Loaded 10000 queries

=== Warming up ===

=== Benchmarks ===
Tantivy only: 10000 queries in 2.35s = 4260 QPS
Benchmarking Tantivy + get_query_ids + SQL...
Tantivy only: 10000 queries in 2.38s = 4206 QPS
Tantivy + get_query_ids + SQL (10000 sample): 10000 queries in 4.18s = 2391 QPS
Full flow: 10000 queries in 4.52s = 2215 QPS

=== Summary ===
Tantivy only:        4260 QPS
get_query_id + SQL:  ~2391 QPS
Full flow:           2215 QPS
```

### Geocoder API Comparison

```
============================================================
VALIDATION REPORT
============================================================

Total records:    4000
Got IBGE result:  3628 (90.7%)
No IBGE result:   372 (9.3%)

[Performance]
  Total time:     92.94s
  QPS:            43.0 queries/s
  Per query:      23.23ms

[Distance (m)]
  Mean:   8793.5
  Median: 67.1
  Max:    7649569.0
  <=100m:  1997 (55.0%)
  <=1km:   2967 (81.8%)

[Text Similarity]
  Street name:       0.683
  Neighborhood:      0.723
  Zip code:          0.723
```
