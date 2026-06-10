# openaddrbr/core — Geocoder & LocationSearch

## Installation

```bash
# Install from GitHub
pip install git+https://github.com/jpsamarino/OpenAddrBR.git

# Download data (~10GB)
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

**Embedding models:** The geocoder uses sentence transformer models (paraphrase-xlmr) to convert street names into dense vector embeddings. This embedding conversion is the most computationally expensive step — it can be slow on CPU, especially for batch operations.

**GPU acceleration (CUDA):** For high-throughput workloads, the library supports CUDA (NVIDIA GPUs) via PyTorch. Enable it by setting the backend to `cuda` or `onnx-int8`:
```python
geocoder = Geocoder(backend="cuda")  # Requires NVIDIA GPU
```
GPUs shine at scale — for hundreds of millions of addresses, CUDA provides 10-50x speedup. For thousands of addresses, CPU is usually sufficient (~100 addresses/second in a modern CPU).

**Example:**

```python
from openaddrbr.core import Geocoder

geocoder = Geocoder()
result = geocoder.geocode(
    street="Rua Marcelina",
    neighborhood="Vila Romana",
    city="São Paulo",
    state="SP",
    zip_code="04071-080",
    number=142,
)
print(result)
```

**Output:**

```json
{
  "lat": -23.530421,
  "long": -46.693946,
  "street_name": "Rua Marcelina",
  "neighborhood": "Vila Romana",
  "city": "São Paulo",
  "state": "SP",
  "zip_code": "05044010",
  "number": 142,
  "ref_number_lat_long": 140,
  "address": "Rua Marcelina, 142, Vila Romana, São Paulo - SP, 05044010"
}
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
    AddressRequest(city="Rio de Janeiro", state="RJ", street="Av Brasil", neighborhood="Centro", zip_code="20010-000", street_number=382),
]
results = geocoder.geocode_batch(addresses)
for r in results:
    print(r)
```

**Output:**

```json
[
  {
    "lat": -23.530421,
    "long": -46.693946,
    "street_name": "Rua Marcelina",
    "neighborhood": "Vila Romana",
    "city": "São Paulo",
    "state": "SP",
    "zip_code": "05044010",
    "number": 142,
    "ref_number_lat_long": 140,
    "address": "Rua Marcelina, 142, Vila Romana, São Paulo - SP, 05044010"
  },
  {
    "lat": -22.864598,
    "long": -43.429388,
    "street_name": "Avenida Brasil",
    "neighborhood": "Coelho Neto",
    "city": "Rio de Janeiro",
    "state": "RJ",
    "zip_code": "20010000",
    "number": 500,
    "ref_number_lat_long": 382,
    "address": "Avenida Brasil, 500, Coelho Neto, Rio de Janeiro - RJ, 20010000"
  }
]
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

```json
[
  {
    "city_code": 3550308,
    "city_name": "São Paulo",
    "city_normalized": "SAO PAULO",
    "state_code": "SP",
    "latitude": -23.660746,
    "longitude": -46.660769
  },
  {
    "city_code": 2412609,
    "city_name": "São Paulo do Potengi",
    "city_normalized": "SAO PAULO DO POTENGI",
    "state_code": "RN",
    "latitude": -5.893018,
    "longitude": -35.759248
  },
  {
    "city_code": 1303908,
    "city_name": "São Paulo de Olivença",
    "city_normalized": "SAO PAULO DE OLIVENCA",
    "state_code": "AM",
    "latitude": -3.462009,
    "longitude": -68.943902
  }
]
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

```json
[
  {
    "neighborhood_name": "Jardim Vila Mariana",
    "neighborhood_normalized": "JARDIM VILA MARIANA",
    "city_code": 3550308,
    "latitude": -23.590027,
    "longitude": -46.630295
  },
  {
    "neighborhood_name": "Parque Novo Mundo",
    "neighborhood_normalized": "PARQUE NOVO MUNDO",
    "city_code": 3550308,
    "latitude": -23.507527,
    "longitude": -46.569041
  },
  {
    "neighborhood_name": "Vila Maria",
    "neighborhood_normalized": "VVILA MARIA",
    "city_code": 3550308,
    "latitude": -23.503524,
    "longitude": -46.582151
  }
]
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

```json
[
  {
    "street_id": 2840143,
    "street_name": "Rua Marcelina",
    "street_normalized": "RUA MARCELINA",
    "neighborhood_name": "Vila Romana",
    "neighborhood_normalized": "VILA ROMANA",
    "zip_codes": [5044010],
    "latitude": -23.530424,
    "longitude": -46.694252
  },
  {
    "street_id": 2840143,
    "street_name": "Rua Marcelina",
    "street_normalized": "RUA MARCELINA",
    "neighborhood_name": "Vila Pompeia",
    "neighborhood_normalized": "VILA POMPEIA",
    "zip_codes": [5044010],
    "latitude": -23.530459,
    "longitude": -46.693021
  }
]
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
    city_normalized: str    # Normalized name (uppercase, for search)
    state_code: str          # State code
    latitude: float          # Centroid latitude
    longitude: float         # Centroid longitude
```

#### NeighborhoodInfo

```python
@dataclass
class NeighborhoodInfo:
    neighborhood_name: str        # Neighborhood name
    neighborhood_normalized: str  # Normalized name (uppercase)
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
    street_normalized: str        # Normalized name (uppercase)
    neighborhood_name: str        # Neighborhood name
    neighborhood_normalized: str  # Normalized neighborhood name (uppercase)
    zip_codes: list[int]         # List of CEPs (as integers)
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

| Function | QPS | Per query | Match rate |
|----------|-----|-----------|------------|
| geocode() | 43.0 | 23.23ms | 90.7% |
| geocode_batch() | 122.3 | 8.17ms | 90.7% |

**Distance accuracy (geocode_batch, 4000 addresses):**
- Median: 67.1m
- <=100m: 55.0%
- <=1km: 81.8%

**What affects performance:**

1. **geocode() single**: CEP lookup when available (fast), otherwise embeds street name via sentence transformer (CPU-intensive, ~23ms on CPU).
2. **geocode_batch()**: Groups addresses by city/street for batch embedding — 3x faster than single queries (~8ms each, 122 QPS).
3. **GPU acceleration**: `backend="cuda"` speeds up embedding 10-50x for large batches.
4. **CEP availability**: Single-street CEPs skip embedding entirely (fastest path).

> **Benchmark environment:** Intel i7-14700, 32GB RAM, CPU only (no GPU). Results may vary with different hardware.

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
| geocode_batch() | 8.17 | Batch encoding — 3x faster |
| geocode() single | 23.23 | Slowest — embedding on CPU |
| geocode_batch (GPU) | ~2ms each | 10x faster with CUDA |

---

