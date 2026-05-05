# OpenAddrBR — Design Specification

## 1. Overview

**What it is:** A Python library for Brazilian address geocoding using vector search (usearch) + SQLite database (sgeobr.db).

**Why it exists:** Encapsulates the existing single-file `ibge_geocoder.py` into a modular, installable package with automatic data management via Hugging Face.

---

## 2. Package Structure

```
openaddrbr/
├── __init__.py           # public API: geocode, get_city_info, search_by_cep, get_geo_info_batch
├── pyproject.toml        # project metadata, dependencies, entry points

├── core/
│   ├── __init__.py
│   ├── models/           # data classes (CityInfo, GeoLocation, StreetCluster, etc)
│   │   ├── __init__.py
│   │   └── _models.py
│   └── interfaces/        # protocol definitions (GeoCoder, CityFinder, etc)
│       ├── __init__.py
│       └── _protocols.py

├── data/
│   ├── __init__.py
│   ├── _db.py             # SQLite connection management
│   ├── _usearch.py         # usearch index loading
│   ├── _hf_downloader.py  # Hugging Face data download
│   └── _config.py         # data path configuration

├── services/
│   ├── __init__.py
│   ├── _city.py           # get_city_info implementation
│   ├── _cep.py            # search_by_cep implementation
│   ├── _geocode.py         # geocode implementation
│   └── _batch.py          # get_geo_info_batch implementation

├── cli/
│   ├── __init__.py
│   └── _commands.py       # CLI entry point (download command)

└── utils/
    ├── __init__.py
    ├── _text.py            # text normalization, ascii conversion
    └── _matching.py        # find_best_street_match, text_similarity
```

**Additional directories (root level):**

```
tests/          # pytest unit tests
benchmarks/     # performance benchmarks
docs/
```

---

## 3. Public API

### Installation

```bash
pip install openaddrbr
```

### First Use

On first use, if data is not found, automatically downloads ~5GB from Hugging Face to a local cache directory.

### Manual Data Configuration

```python
from openaddrbr import set_data_path

set_data_path("/custom/path/to/data")
```

### Available Functions

```python
from openaddrbr import (
    geocode,             # geocode a single address
    get_city_info,       # find city code by name + state
    search_by_cep,       # search street by CEP
    get_geo_info_batch,  # batch geocoding
)
```

Each function can be imported independently — no need to instantiate a class.

---

## 4. Modules

### 4.1 core/models

Data classes that represent domain objects:

- `CityInfo` — city code, name, state
- `GeoLocation` — lat/long with address info
- `StreetCluster` — group of address variations for a street
- `NormalizedAddress` — preprocessed address for matching
- `AddressRequest` — input for batch operations
- `GeoLocationResult` — full geocoding result with formatted address

### 4.2 core/interfaces

Protocols (structural subtyping):

- `CityFinder` — protocol for finding city info by name/state
- `StreetSearcher` — protocol for searching streets (by CEP or vector)
- `GeoCoder` — protocol for full geocoding (combines CityFinder + StreetSearcher)
- `BatchGeocoder` — protocol for batch operations

### 4.3 data/_db.py

SQLite connection management:

- Lazy connection to `sgeobr.db`
- Row factory for dict-like access
- Connection pooling (single connection, reused)

### 4.4 data/_usearch.py

usearch index loading:

- Lazy loading of city-specific `.usearch` files
- LRU cache for index instances
- Path resolution from config

### 4.5 data/_hf_downloader.py

Hugging Face integration:

- Download manager for the ~5GB data bundle
- Checksum verification
- Progress reporting
- Configurable download directory

### 4.6 data/_config.py

Data path management:

- Default: `~/.openaddrbr/data/`
- Override via `OPENADDRBR_DATA_PATH` env var or `set_data_path()`
- Auto-detect if data exists

### 4.7 services/_city.py

`get_city_info(city_name: str, state_code: str) -> CityInfo | None`

- Normalizes input to uppercase ASCII
- Queries `cities` table in sgeobr.db
- Returns CityInfo or None
- LRU cached

### 4.8 services/_cep.py

`search_by_cep(zip_code: str, street_norm: str, neighborhood_norm: str) -> StreetCluster | None`

- Queries `address` table by zip_code
- Builds StreetCluster objects
- Uses `find_best_street_match` for disambiguation
- Checks `multi_street_ceps` table

### 4.9 services/_geocode.py

`geocode(street: str, neighborhood: str, city: str, state: str, zip_code: str | None = None, number: int = 0) -> GeoLocationResult | None`

- Normalizes all inputs
- 1st try: CEP search (if not multi-street CEP)
- Fallback: vector search via usearch
- Builds and returns full GeoLocationResult

### 4.10 services/_batch.py

`get_geo_info_batch(addresses: list[AddressRequest], batch_size: int = 16) -> list[GeoLocationResult | None]`

- Batch encoding via SentenceTransformer
- Groups by city_code + street_norm for efficiency
- Returns results in original order (preserves None for failed lookups)

### 4.11 utils/_text.py

- `text_to_ascii()` — converts Brazilian chars to ASCII
- `normalize_text()` — uppercase + ASCII
- Used across all services

### 4.12 utils/_matching.py

- `find_best_street_match()` — chooses best StreetCluster
- `text_similarity()` — string similarity metric

---

## 5. CLI

### Commands

```bash
openaddrbr download          # download data from Hugging Face
openaddrbr download --force  # re-download even if exists
openaddrbr info              # show data version and location
```

### Entry Point

Defined in `pyproject.toml` as console script:
```toml
[project.scripts]
openaddrbr = "openaddrbr.cli:_main"
```

---

## 6. Dependencies

All required dependencies installed with base package:

- `usearch` — vector search index
- `sentence-transformers` — text encoding
- `numpy`
- `sqlite3` (stdlib)
- `huggingface_hub` — for data download

No optional extras — everything bundled.

---

## 7. Data Flow

```
User code
    │
    ▼
services/ (public functions)
    │
    ├─► data/_db.py        (SQLite queries)
    ├─► data/_usearch.py   (vector index)
    ├─► data/_hf_downloader.py (auto-download if needed)
    │
    ▼
core/models/ (data structures)
```

Services are stateless — they receive everything they need or pull from data layer. No service holds state.

---

## 8. Error Handling

- **City not found:** returns `None` (not an exception)
- **CEP not found:** returns `None`
- **Data not downloaded:** triggers auto-download → if fails, raises `DataNotFoundError`
- **Invalid number:** treated as 0 (existing behavior preserved)

---

## 9. Testing Strategy

```
tests/
├── unit/
│   ├── test_models.py
│   ├── test_city.py
│   ├── test_cep.py
│   ├── test_geocode.py
│   └── test_text.py
├── fixtures/
│   └── sample_addresses.py
└── conftest.py
```

- Unit tests mock SQLite and usearch
- Fixtures for sample addresses
- pytest as test runner

---

## 10. Benchmarks

```
benchmarks/
├── test_geocode_performance.py   # single geocoding latency
├── test_batch_performance.py     # throughput for batch
└── test_vector_search.py        # usearch lookup speed
```

Run with: `pytest benchmarks/`

---

## 11. Version and Release

- Initial version: `0.1.0`
- Data versioning tracked separately (tied to HF dataset version)
- Semantic versioning for the library

---

## 12. Out of Scope (for now)

- Web API / FastAPI wrapper
- Async support
- Database write operations
- Non-Brazilian addresses