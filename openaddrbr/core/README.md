# openaddrbr/core — Geocoder & LocationSearch

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/jpsamarino/OpenAddrBR.git

# Download data (~10GB) — IBGE census, Receita Federal, street data
python -m openaddrbr download

# Auto-tune performance (runs benchmark, detects best backend, creates .env)
python -m openaddrbr setup
```

Works on Windows, Linux, and Mac. Python 3.12+ required.

---

## 1. Overview

Geocoder + LocationSearch Python library for Brazilian address geocoding using open data (IBGE census, Receita Federal, and other public datasets).

- **Geocoder**: converts address → lat/long coordinates using vector search + IBGE data
- **LocationSearch**: fast autocomplete for cities, neighborhoods, and streets using Tantivy ngram search

### Architecture

```
Geocoder:
  address → CEP check (fast) OR vector search (embedding fallback) → lat/long

LocationSearch:
  query → Tantivy ngram search → SQL lookup → scoring → results
```

---

## 2. How to Use

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

Converts a Brazilian address into lat/long coordinates. Uses CEP lookup when available (fast and accurate), falls back to vector search (embedding) when CEP is unavailable or belongs to a multi-street zone.

**Example:**

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

Geocodes multiple addresses in batch. Groups addresses by city and street to optimize batch encoding. Preserves original result order.

**Example:**

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

Searches for cities by name using Tantivy ngram search. Returns up to `limit` cities sorted by relevance.

**Example:**

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

Searches for neighborhoods by name within a specific city (filtered by IBGE `city_code`). Returns up to `limit` neighborhoods sorted by relevance.

**Example:**

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

Searches for streets by name within a specific city. The `autocomplete_query=True` parameter optimizes for progressive typing (prefix search). The `neighborhood` parameter boosts results matching the specified neighborhood.

**Example:**

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

### 2.3 Return Types

#### AddressInfo

```python
@dataclass
class AddressInfo:
    lat: float              # Latitude
    long: float             # Longitude
    street_name: str        # Street name
    neighborhood: str       # Neighborhood name
    city: str               # City name
    state: str              # State code
    zip_code: str           # CEP (postal code)
    number: int             # Street number
    ref_number_lat_long: int  # Flag if lat/long came from street number
    address: str = ""       # Formatted address string
```

#### CityInfo

```python
@dataclass
class CityInfo:
    city_code: int          # IBGE city code
    city_name: str          # City name
    city_normalized: str    # Normalized name (for search)
    state_code: str          # State code
    latitude: float          # Centroid latitude
    longitude: float         # Centroid longitude
```

#### NeighborhoodInfo

```python
@dataclass
class NeighborhoodInfo:
    neighborhood_name: str        # Neighborhood name
    neighborhood_normalized: str  # Normalized name
    city_code: int                # IBGE city code
    latitude: float               # Centroid latitude
    longitude: float              # Centroid longitude
```

#### StreetSegmentInfo

```python
@dataclass
class StreetSegmentInfo:
    street_id: int                # Unique street ID
    street_name: str              # Street name
    street_normalized: str        # Normalized name
    neighborhood_name: str        # Neighborhood name
    neighborhood_normalized: str  # Normalized neighborhood name
    zip_codes: list[str]          # List of CEPs
    latitude: float               # Centroid latitude
    longitude: float              # Centroid longitude
```

---

## 3. Roadmap

| Function | Class | Status | Description |
|----------|-------|--------|-------------|
| geocode | Geocoder | ✅ | Geocode address to lat/long |
| geocode_batch | Geocoder | ✅ | Batch geocode multiple addresses |
| geocode_city | Geocoder | 📋 | Geocode by city only |
| geocode_neighborhood | Geocoder | 📋 | Geocode by neighborhood |
| geocode_street | Geocoder | 📋 | Geocode street without number |
| geocode_street_number | Geocoder | 📋 | Geocode street with specific number |
| reverse_geocode | Geocoder | 📋 | Given lat/long → address |
| get_addresses_in_radius | Geocoder | 📋 | List addresses in radius |
| get_street_numbers | Geocoder | 📋 | Search street numbers |
| search_cities | LocationSearch | ✅ | Search cities by name |
| search_neighborhoods | LocationSearch | ✅ | Search neighborhoods by name |
| search_streets | LocationSearch | ✅ | Search streets by name |
| autocomplete_street | LocationSearch | 📋 | Street autocomplete |
| autocomplete_addresse | LocationSearch | 📋 | Full address autocomplete |
| parse_address | LocationSearch | 📋 | Brazilian address parser |
| search_cep | LocationSearch | 📋 | Search by CEP |

---

## 4. Performance

### 4.1 Geocoder

| Metric | Value |
|--------|-------|
| QPS (queries per second) | 43.0 |
| Time per query | 23.23ms |
| Match rate (IBGE result) | 90.7% |
| Addresses <=100m | 55.0% |
| Addresses <=1km | 81.8% |

**What affects performance:**

1. **CEP available (fastest)**: When CEP belongs to a single-street zone (`is_multi_street_cep` returns false), lookup uses CEP directly — no vector search needed.
2. **Vector search fallback (slower)**: When no CEP is provided or it's a multi-street CEP, the system embeds the street name and searches the vector index (usearch). This is the slower path.
3. **Batch size**: `geocode_batch` groups addresses by city/street to optimize batch encoding.

### 4.2 LocationSearch

LocationSearch follows this flow: **Tantivy search → SQL lookup → scoring**.

#### search_cities

| Test | Queries | Avg ms | Accuracy |
|------|---------|--------|----------|
| Full name | 100 | 2.29 | 100.0% |
| Abbreviation | 100 | 0.10 | 74.0% |
| Partial | 100 | 0.09 | 34.0% |
| First 2 chars | 100 | 0.05 | 8.0% |
| First 3 chars | 100 | 0.07 | 37.0% |

**Overall avg time: 0.52ms | Overall avg accuracy: 50.6%**

#### search_neighborhoods

| Test | Queries | Avg ms | Accuracy |
|------|---------|--------|----------|
| Full name | 10000 | 1.7771 | 99.7% |
| Abbreviation | 9999 | 0.7514 | 99.7% |
| Partial | 10000 | 0.5314 | 95.6% |
| First 2 chars | 9984 | 0.0760 | 79.2% |
| First 3 chars | 9984 | 0.2278 | 86.7% |

**Overall avg time: 0.6727ms | Overall avg accuracy: 92.2%**

#### search_streets

| Test | Normal ms | Auto ms | Speedup | Acc Normal | Acc Auto |
|------|-----------|---------|---------|------------|----------|
| Full name | 1.5149 | 0.4492 | 3.37x | 100.0% | 98.1% |
| Abbreviation | 1.0251 | 0.3325 | 3.08x | 98.7% | 97.6% |
| Partial | 0.4992 | 0.2477 | 2.02x | 85.7% | 82.9% |
| First 2 chars | 0.3665 | 0.3574 | 1.03x | 10.0% | 10.0% |
| First 3 chars | 0.3921 | 0.3361 | 1.17x | 14.0% | 14.0% |

**Normal mode - Avg time: 0.7596ms, Avg accuracy: 61.7%**
**Auto mode - Avg time: 0.3446ms, Avg accuracy: 60.5%**
**Speedup: 2.20x**

`autocomplete_query=True` is **2.2x faster** than normal mode with similar accuracy. Use for progressive typing.

**Full flow breakdown (Tantivy + SQL + scoring):**

| Stage | QPS |
|-------|-----|
| Tantivy only | 4260 |
| get_query_id + SQL | 2391 |
| Full flow | 2215 |

### 4.3 General Comparison

| Function | Avg ms | Notes |
|----------|--------|-------|
| search_cities (abbreviation) | 0.10 | Fastest |
| search_neighborhoods (first 2 chars) | 0.08 | Very fast |
| search_streets (autocomplete) | 0.34 | Good speed |
| search_cities (full name) | 2.29 | Slightly slower |
| search_neighborhoods (full name) | 1.78 | Medium |
| geocode (single) | 23.23 | Slowest (vector search) |

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

### Geocoder Benchmark

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