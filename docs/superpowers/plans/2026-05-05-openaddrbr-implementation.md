# OpenAddrBR Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor single-file `ibge_geocoder.py` into modular package structure with all existing tests passing.

**Architecture:** Split monolithic IBGEGeocoder into stateless services (city, cep, geocode, batch) with core/models for data classes, data/ for DB/usearch access, and utils/ for text matching. Public API exposes standalone functions that delegate to services.

**Tech Stack:** Python 3.11+, usearch, sentence-transformers, rapidfuzz, huggingface_hub, pytest

---

## File Structure

```
openaddrbr/
├── __init__.py              # public API: geocode, get_city_info, search_by_cep, get_geo_info_batch, set_data_path
├── pyproject.toml           # project metadata, dependencies, entry points
├── core/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── _models.py       # CityInfo, GeoLocation, StreetCluster, NormalizedAddress, AddressRequest, GeoLocationResult
│   └── interfaces/
│       ├── __init__.py
│       └── _protocols.py    # GeoCoder, CityFinder, StreetSearcher, BatchGeocoder protocols
├── data/
│   ├── __init__.py
│   ├── _config.py           # data path management (default ~/.openaddrbr/data/, env var override)
│   ├── _db.py               # SQLite connection management (lazy, singleton)
│   ├── _usearch.py          # usearch index loading (lazy, LRU cached)
│   └── _hf_downloader.py    # Hugging Face download manager (resume-capable)
├── services/
│   ├── __init__.py
│   ├── _city.py             # get_city_info implementation
│   ├── _cep.py              # search_by_cep implementation
│   ├── _geocode.py          # geocode implementation
│   └── _batch.py            # get_geo_info_batch implementation
├── cli/
│   ├── __init__.py
│   └── _commands.py          # CLI: download, info
└── utils/
    ├── __init__.py
    ├── _text.py              # text_to_ascii, normalize_text
    └── _matching.py          # text_similarity, find_best_street_match

tests/
├── unit/
│   ├── test_address_matching.py
│   ├── test_get_cod_municipio.py   # will be renamed to test_city.py
│   ├── test_search_by_cep.py
│   ├── test_search_logradouro_vector.py
│   └── test_similarity.py
├── integration/
│   └── test_ibge_geocoder.py
└── fixtures/
    └── (sample addresses)

benchmarks/
```

---

## Task 1: Project Setup - pyproject.toml and basic structure

**Files:**
- Create: `openaddrbr/pyproject.toml`
- Create: `openaddrbr/__init__.py`
- Create: `openaddrbr/core/__init__.py`
- Create: `openaddrbr/core/models/__init__.py`
- Create: `openaddrbr/core/models/_models.py`
- Create: `openaddrbr/core/interfaces/__init__.py`
- Create: `openaddrbr/core/interfaces/_protocols.py`
- Create: `openaddrbr/data/__init__.py`
- Create: `openaddrbr/data/_config.py`
- Create: `openaddrbr/data/_db.py`
- Create: `openaddrbr/data/_usearch.py`
- Create: `openaddrbr/data/_hf_downloader.py`
- Create: `openaddrbr/services/__init__.py`
- Create: `openaddrbr/services/_city.py`
- Create: `openaddrbr/services/_cep.py`
- Create: `openaddrbr/services/_geocode.py`
- Create: `openaddrbr/services/_batch.py`
- Create: `openaddrbr/cli/__init__.py`
- Create: `openaddrbr/cli/_commands.py`
- Create: `openaddrbr/utils/__init__.py`
- Create: `openaddrbr/utils/_text.py`
- Create: `openaddrbr/utils/_matching.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "openaddrbr"
version = "0.1.0"
description = "Brazilian address geocoder using vector search (usearch) + SQLite (sgeobr.db)"
readme = "README.md"
requires-python = ">=3.11"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "your@email.com"}]
keywords = ["geocoding", "brazil", "ibge", "address", "vector-search"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "usearch",
    "sentence-transformers",
    "numpy",
    "rapidfuzz",
    "huggingface_hub",
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
]

[project.scripts]
openaddrbr = "openaddrbr.cli:_main"

[tool.setuptools.packages.find]
where = ["."]
include = ["openaddrbr*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

- [ ] **Step 2: Create openaddrbr/core/models/_models.py**

```python
"""Domain models for OpenAddrBR."""

from dataclasses import dataclass, field
from typing import NamedTuple


@dataclass(slots=True)
class StreetCluster:
    """Group of address variations grouped by street_id for matching."""

    street_id: int
    street_normalized: set[str] = field(default_factory=set)
    neighborhood_normalized: set[str] = field(default_factory=set)


class CityInfo(NamedTuple):
    """City information from IBGE."""

    city_code: int
    city_name: str
    state_code: str


class GeoLocation(NamedTuple):
    """Geo location result."""

    address_id: int
    latitude: float
    longitude: float
    address_number: int


@dataclass(slots=True)
class AddressRequest:
    """Address request model for geocoding."""

    city: str
    state: str
    street: str = ""
    neighborhood: str = ""
    zip_code: str | None = None
    street_number: int = 0


@dataclass(slots=True)
class GeoLocationResult:
    """Result of a geocoding operation."""

    lat: float
    long: float
    street_name: str
    neighborhood: str
    city: str
    state: str
    zip_code: str
    number: int
    ref_number_lat_long: int
    address: str = ""


class NormalizedAddress(NamedTuple):
    """Normalized address data used in batch processing."""

    order: int
    address: AddressRequest
    city_info: CityInfo | None
    street_norm: str
    neighborhood_norm: str
    zip_code: str | None
    number: int
```

- [ ] **Step 3: Create openaddrbr/core/models/__init__.py**

```python
"""Core models package."""

from openaddrbr.core.models._models import (
    AddressRequest,
    CityInfo,
    GeoLocation,
    GeoLocationResult,
    NormalizedAddress,
    StreetCluster,
)

__all__ = [
    "StreetCluster",
    "CityInfo",
    "GeoLocation",
    "NormalizedAddress",
    "AddressRequest",
    "GeoLocationResult",
]
```

- [ ] **Step 4: Create openaddrbr/core/interfaces/_protocols.py**

```python
"""Protocol definitions for structural subtyping."""

from typing import Protocol, runtime_checkable
from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocationResult,
    StreetCluster,
)
import numpy as np


@runtime_checkable
class CityFinder(Protocol):
    """Protocol for finding city info by name and state."""

    def get_city_info(self, city_name: str, state_code: str) -> CityInfo | None:
        ...


@runtime_checkable
class StreetSearcher(Protocol):
    """Protocol for searching streets by CEP or vector."""

    def search_by_cep(
        self,
        zip_code: str,
        street_norm: str,
        neighborhood_norm: str,
    ) -> StreetCluster | None:
        ...

    def search_vector(
        self, embedding: np.ndarray, city_code: int, limit: int = 20
    ) -> list[str]:
        ...


@runtime_checkable
class GeoCoder(Protocol):
    """Protocol for full geocoding operations."""

    def geocode(
        self,
        street: str,
        neighborhood: str,
        city: str,
        state: str,
        zip_code: str | None = None,
        number: int = 0,
    ) -> GeoLocationResult | None:
        ...


@runtime_checkable
class BatchGeocoder(Protocol):
    """Protocol for batch geocoding operations."""

    def get_geo_info_batch(
        self,
        addresses: list[AddressRequest],
        batch_size: int = 16,
    ) -> list[GeoLocationResult | None]:
        ...
```

- [ ] **Step 5: Create openaddrbr/core/interfaces/__init__.py**

```python
"""Core interfaces package."""

from openaddrbr.core.interfaces._protocols import (
    BatchGeocoder,
    CityFinder,
    GeoCoder,
    StreetSearcher,
)

__all__ = [
    "CityFinder",
    "StreetSearcher",
    "GeoCoder",
    "BatchGeocoder",
]
```

- [ ] **Step 6: Create openaddrbr/core/__init__.py**

```python
"""Core package - models and interfaces."""

from openaddrbr.core.models import *
from openaddrbr.core.interfaces import *

__all__ = []  # re-export all from subpackages
```

- [ ] **Step 7: Commit**

```bash
git add openaddrbr/pyproject.toml openaddrbr/core/
git commit -m "feat: add project structure and core models"
```

---

## Task 2: Utils - text normalization and matching

**Files:**
- Modify: `openaddrbr/utils/_text.py`
- Modify: `openaddrbr/utils/_matching.py`
- Modify: `openaddrbr/utils/__init__.py`

- [ ] **Step 1: Create openaddrbr/utils/_text.py**

```python
"""Text normalization utilities."""

from unicodedata import normalize


def text_to_ascii(text: str) -> str:
    """
    Convert a given text to its ASCII representation by removing any characters
    with accents or diacritics. The function normalizes the input text using
    Unicode normalization form 'NFKD' and then encodes it into ASCII, ignoring
    any non-ASCII characters.

    Args:
        text (str): The input string which may contain accented characters.

    Returns:
        str: The ASCII representation of the input string with accents removed.
    """
    return normalize('NFKD', text or "").encode('ASCII', 'ignore').decode('ASCII')


def normalize_text(text: str) -> str:
    """Normalize text to uppercase ASCII."""
    return text_to_ascii(text).upper()
```

- [ ] **Step 2: Create openaddrbr/utils/_matching.py**

```python
"""Address matching utilities."""

from rapidfuzz import fuzz
from openaddrbr.utils._text import text_to_ascii
from openaddrbr.core.models import StreetCluster


def text_similarity(
    text1: str, text2: str, case_sensitive: bool = True, ascii: bool = False
) -> float:
    """Similarity between two texts using rapidfuzz ratio."""
    t1 = text1 or ""
    t2 = text2 or ""

    if ascii:
        t1 = text_to_ascii(t1)
        t2 = text_to_ascii(t2)

    if not case_sensitive:
        t1 = t1.upper()
        t2 = t2.upper()

    if not t1 or not t2:
        return 0.0

    return fuzz.ratio(t1, t2) / 100


def make_similarity_func(normalize_func=None):
    """Factory that creates a similarity function with fixed normalization."""
    def similarity(text1: str, text2: str) -> float:
        t1 = normalize_func(text1) if normalize_func else (text1 or "")
        t2 = normalize_func(text2) if normalize_func else (text2 or "")
        if not t1 or not t2:
            return 0.0
        return fuzz.ratio(t1, t2) / 100
    return similarity


def find_best_street_match(
    clusters: list[StreetCluster],
    ref_street_norm: str,
    ref_neighborhood_norm: str,
    min_street_similarity: float = 0.7,
    min_neighborhood_similarity: float = 0.7,
    similarity_func=text_similarity,
) -> StreetCluster | None:
    """Find the best matching StreetCluster given reference street and neighborhood."""
    weight_street = 0.7
    weight_neighborhood = 1.0 - weight_street
    best_cluster = None
    best_total_score = 0.0

    for summary in clusters:
        best_s_sim = max(
            (
                similarity_func(ref_street_norm, s or "")
                for s in summary.street_normalized
            ),
            default=0.0,
        )

        if best_s_sim > min_street_similarity:
            best_n_sim = max(
                (
                    similarity_func(ref_neighborhood_norm, n or "")
                    for n in summary.neighborhood_normalized
                ),
                default=1.0 if not ref_neighborhood_norm else 0.0,
            )

            if best_n_sim > min_neighborhood_similarity:
                total_score = (
                    weight_street * best_s_sim + weight_neighborhood * best_n_sim
                ) / (weight_street + weight_neighborhood)
                if total_score > best_total_score:
                    best_total_score = total_score
                    best_cluster = summary

    return best_cluster
```

- [ ] **Step 3: Create openaddrbr/utils/__init__.py**

```python
"""Utils package."""

from openaddrbr.utils._text import text_to_ascii, normalize_text
from openaddrbr.utils._matching import text_similarity, find_best_street_match, make_similarity_func

__all__ = [
    "text_to_ascii",
    "normalize_text",
    "text_similarity",
    "find_best_street_match",
    "make_similarity_func",
]
```

- [ ] **Step 4: Commit**

```bash
git add openaddrbr/utils/
git commit -m "feat: add text normalization and matching utilities"
```

---

## Task 3: Data Layer - config, db, usearch, hf_downloader

**Files:**
- Create: `openaddrbr/data/_config.py`
- Create: `openaddrbr/data/_db.py`
- Create: `openaddrbr/data/_usearch.py`
- Create: `openaddrbr/data/_hf_downloader.py`
- Create: `openaddrbr/data/__init__.py`

- [ ] **Step 1: Create openaddrbr/data/_config.py**

```python
"""Data path configuration management."""

import os
from pathlib import Path
from typing import Optional

# Environment variable for data path override
ENV_DATA_PATH = "OPENADDRBR_DATA_PATH"

# Default data directory (user home/.openaddrbr/data)
DEFAULT_DATA_DIR = Path.home() / ".openaddrbr" / "data"

# Singleton state
_data_path: Optional[Path] = None


def get_data_path() -> Path:
    """Get the current data path, checking env var first."""
    global _data_path
    if _data_path is not None:
        return _data_path

    env_path = os.environ.get(ENV_DATA_PATH)
    if env_path:
        return Path(env_path)

    return DEFAULT_DATA_DIR


def set_data_path(path: str | Path) -> None:
    """Set a custom data path."""
    global _data_path
    _data_path = Path(path)


def get_sgeodb_path() -> Path:
    """Get path to sgeobr.db."""
    return get_data_path() / "sgeobr.db"


def get_usearch_dir() -> Path:
    """Get path to usearch indices directory."""
    return get_data_path() / "usearch_v2"


def get_model_path() -> Path:
    """Get path to sentence transformer model."""
    return get_data_path() / "model_paraphrase_xlmr"


def ensure_data_path() -> None:
    """Ensure the data directory exists."""
    get_data_path().mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 2: Create openaddrbr/data/_db.py**

```python
"""SQLite database connection management."""

import sqlite3
from functools import lru_cache
from typing import Optional

_conn: Optional[sqlite3.Connection] = None


def get_connection() -> sqlite3.Connection:
    """Get a lazy SQLite connection to sgeobr.db."""
    global _conn
    if _conn is None:
        from openaddrbr.data._config import get_sgeodb_path
        db_path = get_sgeodb_path()
        if not db_path.exists():
            raise FileNotFoundError(
                f"Database not found at {db_path}. "
                "Please download data using: python -m openaddrbr download"
            )
        _conn = sqlite3.connect(db_path)
        _conn.row_factory = sqlite3.Row
    return _conn


def close_connection() -> None:
    """Close the database connection."""
    global _conn
    if _conn:
        _conn.close()
        _conn = None


@lru_cache(maxsize=7000)
def get_city_info_from_db(city_name: str, state_code: str):
    """Query city info from database. Cached."""
    from openaddrbr.utils import normalize_text

    conn = get_connection()
    state = state_code.strip().upper()
    target = normalize_text(city_name)

    query = """
        SELECT city_code, city_name, state_code FROM cities
        WHERE state_code = ?
          AND city_normalized = ?
        LIMIT 1
    """
    row = conn.execute(query, (state, target)).fetchone()
    return row


@lru_cache(maxsize=10000)
def is_multi_street_cep(cep: str) -> bool:
    """Check if CEP has multiple streets. Cached."""
    conn = get_connection()
    query = "SELECT 1 FROM multi_street_ceps WHERE zip_code = ? LIMIT 1"
    result = conn.execute(query, (cep,)).fetchone()
    return result is not None


def query_address_by_cep(zip_code: str, limit: int = 10):
    """Query address rows by zip code."""
    conn = get_connection()
    query = """
        SELECT street_id, street_normalized, neighborhood_normalized
        FROM address
        WHERE zip_code = ?
        ORDER BY street_id, id DESC
        LIMIT ?
    """
    return conn.execute(query, (zip_code, limit)).fetchall()


def query_address_by_street_names(street_names: list[str], city_code: int):
    """Query address rows by street names."""
    if not street_names:
        return []
    conn = get_connection()
    placeholders = ", ".join("?" * len(street_names))
    query = f"""
        SELECT street_id, street_normalized, neighborhood_normalized
        FROM address
        WHERE city_code = ?
          AND street_normalized IN ({placeholders})
        ORDER BY street_id, qt_refs DESC
    """
    return conn.execute(query, [city_code] + street_names).fetchall()


def query_full_address_by_street_id(street_id: int):
    """Query full address info by street_id."""
    conn = get_connection()
    query = """
        SELECT
            street_name, street_normalized,
            neighborhood_name, neighborhood_normalized,
            zip_code, id, source_type
        FROM address
        WHERE street_id = ?
        ORDER BY qt_refs DESC
    """
    return conn.execute(query, (street_id,)).fetchall()


def query_geo_locations(street_id: int, number: int, limit: int = 3):
    """Query geo locations for a street_id."""
    conn = get_connection()
    number = number if number is not None and number < 999999 else 0
    query = """
        SELECT latitude, longitude, address_number, address_id
        FROM geo_locations
        WHERE street_id = ?
        ORDER BY ABS(CAST(address_number AS INTEGER) - ?)
        LIMIT ?
    """
    return conn.execute(query, (street_id, number, limit)).fetchall()


def query_street_query(query_ids: list[int], city_code: int):
    """Query street_query table for vector search results."""
    if not query_ids:
        return []
    conn = get_connection()
    placeholders = ",".join("?" * len(query_ids))
    query = f"""
        SELECT DISTINCT street_normalized
        FROM street_query
        WHERE query_id IN ({placeholders}) AND city_code = ?
    """
    return conn.execute(query, query_ids + [str(city_code)]).fetchall()
```

- [ ] **Step 3: Create openaddrbr/data/_usearch.py**

```python
"""Usearch index loading and management."""

import os
from functools import lru_cache
from typing import Optional

try:
    from usearch.index import Index as usearch_Index
except ImportError:
    usearch_Index = None

from openaddrbr.data._config import get_usearch_dir


@lru_cache(maxsize=100)
def get_city_index(city_code: int) -> Optional["usearch_Index"]:
    """Load usearch city index with LRU cache."""
    if usearch_Index is None:
        return None

    index_path = get_usearch_dir() / f"{city_code}.usearch"
    if not index_path.exists():
        return None
    return usearch_Index(path=str(index_path), view=True)


def search_vector(
    embedding, city_code: int, limit: int = 20
) -> list[int]:
    """Search for query_ids by vector similarity using usearch."""
    index = get_city_index(city_code)
    if index is None:
        return []

    results = index.search(embedding.astype(np.float32), count=limit)
    return [int(r.key) for r in results]
```

- [ ] **Step 4: Create openaddrbr/data/_hf_downloader.py**

```python
"""Hugging Face data download manager."""

from pathlib import Path
from typing import Optional

try:
    from huggingface_hub import snapshot_download
except ImportError:
    snapshot_download = None

from openaddrbr.data._config import get_data_path, ensure_data_path

REPO_ID = "your-org/openaddrbr-data"  # Placeholder - update to actual repo


def download_data(
    repo_id: Optional[str] = None,
    force: bool = False,
    progress_callback=None,
) -> Path:
    """
    Download data from Hugging Face Hub.

    Args:
        repo_id: Hugging Face repository ID. Defaults to openaddrbr-data repo.
        force: Force re-download even if data exists.
        progress_callback: Optional callback(current, total) for progress.

    Returns:
        Path to downloaded data directory.
    """
    if snapshot_download is None:
        raise ImportError(
            "huggingface_hub not installed. Install with: pip install huggingface_hub"
        )

    ensure_data_path()
    data_path = get_data_path()

    actual_repo = repo_id or REPO_ID

    print(f"Downloading data from Hugging Face: {actual_repo}")
    print(f"Destination: {data_path}")

    snapshot_download(
        repo_id=actual_repo,
        local_dir=str(data_path),
        resume_download=True,
        local_files_only=not force,
    )

    print(f"Data downloaded successfully to {data_path}")
    return data_path


def check_data_exists() -> bool:
    """Check if data files exist."""
    from openaddrbr.data._config import get_sgeodb_path, get_usearch_dir

    sgeodb = get_sgeodb_path()
    usearch_dir = get_usearch_dir()

    return sgeodb.exists() and usearch_dir.exists()
```

- [ ] **Step 5: Create openaddrbr/data/__init__.py**

```python
"""Data package - database, usearch, and download management."""

from openaddrbr.data._config import (
    get_data_path,
    set_data_path,
    get_sgeodb_path,
    get_usearch_dir,
    get_model_path,
)
from openaddrbr.data._db import (
    get_connection,
    close_connection,
    get_city_info_from_db,
    is_multi_street_cep,
    query_address_by_cep,
    query_address_by_street_names,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
)
from openaddrbr.data._usearch import get_city_index, search_vector
from openaddrbr.data._hf_downloader import download_data, check_data_exists

__all__ = [
    "get_data_path",
    "set_data_path",
    "get_sgeodb_path",
    "get_usearch_dir",
    "get_model_path",
    "get_connection",
    "close_connection",
    "get_city_info_from_db",
    "is_multi_street_cep",
    "query_address_by_cep",
    "query_address_by_street_names",
    "query_full_address_by_street_id",
    "query_geo_locations",
    "query_street_query",
    "get_city_index",
    "search_vector",
    "download_data",
    "check_data_exists",
]
```

- [ ] **Step 6: Commit**

```bash
git add openaddrbr/data/
git commit -m "feat: add data layer (config, db, usearch, hf_downloader)"
```

---

## Task 4: Services - city, cep, geocode, batch

**Files:**
- Modify: `openaddrbr/services/_city.py`
- Modify: `openaddrbr/services/_cep.py`
- Modify: `openaddrbr/services/_geocode.py`
- Modify: `openaddrbr/services/_batch.py`
- Modify: `openaddrbr/services/__init__.py`

- [ ] **Step 1: Create openaddrbr/services/_city.py**

```python
"""City service - get_city_info implementation."""

from functools import lru_cache

from openaddrbr.core.models import CityInfo
from openaddrbr.data import get_city_info_from_db


@lru_cache(maxsize=7000)
def get_city_info(city_name: str, state_code: str) -> CityInfo | None:
    """
    Get IBGE city info from city name and state code.

    Args:
        city_name: Name of the city (accented, case-insensitive)
        state_code: Two-letter state code (e.g., "SP", "RJ")

    Returns:
        CityInfo with city_code, city_name, state_code or None if not found.
    """
    row = get_city_info_from_db(city_name, state_code)
    if not row:
        return None

    return CityInfo(
        city_code=row["city_code"],
        city_name=row["city_name"],
        state_code=row["state_code"],
    )
```

- [ ] **Step 2: Create openaddrbr/services/_cep.py**

```python
"""CEP search service - search_by_cep implementation."""

from openaddrbr.core.models import StreetCluster
from openaddrbr.data import query_address_by_cep, is_multi_street_cep as _is_multi_street_cep
from openaddrbr.utils import find_best_street_match, normalize_text


@lru_cache(maxsize=10000)
def is_multi_street_cep(cep: str) -> bool:
    """Check if CEP has multiple streets."""
    return _is_multi_street_cep(cep)


def search_by_cep(
    zip_code: str,
    street_norm: str,
    neighborhood_norm: str,
    limit_qt_street: int = 10,
) -> StreetCluster | None:
    """
    Search for street_id by CEP.

    Args:
        zip_code: 8-digit CEP
        street_norm: Normalized street name (uppercase ASCII)
        neighborhood_norm: Normalized neighborhood name
        limit_qt_street: Maximum number of streets to consider

    Returns:
        StreetCluster with best matching street or None.
    """
    rows = query_address_by_cep(zip_code, limit_qt_street)

    if not rows:
        return None

    clusters: list[StreetCluster] = []
    last_street_id = None
    for row in rows:
        sid = row["street_id"]
        if sid != last_street_id:
            clusters.append(StreetCluster(street_id=sid))
            last_street_id = sid
        current = clusters[-1]
        current.street_normalized.add(row["street_normalized"])
        current.neighborhood_normalized.add(row["neighborhood_normalized"])

    return find_best_street_match(
        clusters,
        street_norm,
        neighborhood_norm,
    )
```

- [ ] **Step 3: Create openaddrbr/services/_geocode.py**

```python
"""Geocode service - main geocoding implementation."""

import os
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from openaddrbr.core.models import (
    AddressRequest,
    CityInfo,
    GeoLocation,
    GeoLocationResult,
    NormalizedAddress,
    StreetCluster,
)
from openaddrbr.data import (
    check_data_exists,
    download_data,
    query_address_by_street_names,
    query_full_address_by_street_id,
    query_geo_locations,
    query_street_query,
    search_vector as search_vector_index,
)
from openaddrbr.data._config import get_model_path
from openaddrbr.services._city import get_city_info as _get_city_info
from openaddrbr.services._cep import search_by_cep, is_multi_street_cep
from openaddrbr.utils import find_best_street_match, normalize_text, text_similarity

MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

# Thread limiting
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"
os.environ["NUMEXPR_NUM_THREADS"] = "2"

_model: Optional[SentenceTransformer] = None


def _get_model() -> SentenceTransformer:
    """Get or create the sentence transformer model."""
    global _model
    if _model is None:
        model_path = get_model_path()
        if not model_path.exists():
            print(f"[MODEL] Downloading model to {model_path}...")
            model_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_model = SentenceTransformer(MODEL_NAME)
            tmp_model.save(str(model_path))
            print(f"[MODEL] Model saved to local path")
        _model = SentenceTransformer(str(model_path))
        _model.max_seq_length = 128
    return _model


def _encode_street(street_norm: str) -> np.ndarray | None:
    """Encode a single street name to vector."""
    if not street_norm:
        return None
    model = _get_model()
    return model.encode([street_norm], show_progress_bar=False)[0]


def _encode_streets_batch(street_norms: list[str], batch_size: int) -> list[np.ndarray]:
    """Batch encode street names."""
    if not street_norms:
        return []
    return _get_model().encode(
        street_norms, batch_size=batch_size, show_progress_bar=False
    )


def _find_best_geo_location(
    street_id: int, number: int, limit_numbers: int = 3
) -> GeoLocation | None:
    """Find best geo location for street_id and number with parity matching."""
    rows = query_geo_locations(street_id, number, limit_numbers)

    if not rows:
        return None

    ref_is_even = number % 2 == 0

    for row in rows:
        addr_num = row["address_number"]
        if addr_num is None:
            continue
        try:
            addr_int = int(addr_num)
        except (ValueError, TypeError):
            continue

        addr_is_even = addr_int % 2 == 0
        if ref_is_even == addr_is_even:
            return GeoLocation(
                latitude=row["latitude"],
                longitude=row["longitude"],
                address_id=row["address_id"],
                address_number=addr_num,
            )

    # No parity match - return first
    row = rows[0]
    return GeoLocation(
        latitude=row["latitude"],
        longitude=row["longitude"],
        address_id=row["address_id"],
        address_number=int(row["address_number"]),
    )


def _fetch_clusters_by_street_names(
    street_names: list[str], city_code: int
) -> list[StreetCluster]:
    """Fetch and build street clusters from normalized street names."""
    if not street_names:
        return []
    rows = query_address_by_street_names(street_names, city_code)
    if not rows:
        return []

    clusters: list[StreetCluster] = []
    last_street_id = None
    for row in rows:
        sid = row["street_id"]
        if sid != last_street_id:
            clusters.append(StreetCluster(street_id=sid))
            last_street_id = sid
        current = clusters[-1]
        current.street_normalized.add(row["street_normalized"])
        current.neighborhood_normalized.add(row["neighborhood_normalized"])
    return clusters


def _search_by_embedding(
    city_code: int,
    embedding: np.ndarray,
    street_norm: str,
    neighborhood_norm: str,
) -> StreetCluster | None:
    """Search by complete address using vector search + exact SQL."""
    if embedding is None or street_norm is None:
        return None
    query_ids = search_vector_index(embedding, city_code, limit=20)
    if not query_ids:
        return None

    street_rows = query_street_query(query_ids, city_code)
    street_names = [row["street_normalized"] for row in street_rows]
    if not street_names:
        return None

    clusters = _fetch_clusters_by_street_names(street_names, city_code)
    if not clusters:
        return None
    return find_best_street_match(
        clusters, street_norm, neighborhood_norm, min_neighborhood_similarity=0
    )


def _build_result(
    street_cluster: StreetCluster,
    street: str,
    street_norm: str,
    neighborhood_norm: str,
    cep: str | None,
    number: int,
    city_info: CityInfo,
) -> GeoLocationResult | None:
    """Build GeoLocationResult from street_cluster."""
    street_id = street_cluster.street_id
    rows = query_full_address_by_street_id(street_id)

    if not rows:
        return None

    clusters = {"streets": set(), "neighborhoods": set(), "zip_codes": set()}

    for row in rows:
        if row["street_normalized"] in street_cluster.street_normalized:
            clusters["streets"].add((row["street_normalized"], row["street_name"]))
            clusters["neighborhoods"].add(
                (row["neighborhood_normalized"], row["neighborhood_name"])
            )
            if row["zip_code"]:
                clusters["zip_codes"].add(
                    (str(row["zip_code"]).zfill(8), row["id"], row["source_type"])
                )

    geo_result = _find_best_geo_location(street_id, number)
    if geo_result:
        address_id_ref_lat_long = geo_result.address_id
        lat = geo_result.latitude
        long = geo_result.longitude
        number_ref = geo_result.address_number
    else:
        lat, long = 0.0, 0.0
        number_ref = 0
        address_id_ref_lat_long = None

    # Find best matching street
    best_street = (0, "")
    for s_norm, s_accents in clusters["streets"]:
        if s_accents == street:
            best_street = (1, s_accents)
            break
        sim = text_similarity(street_norm, s_norm)
        if sim > best_street[0]:
            best_street = (sim, s_accents)

    # Find best matching neighborhood
    best_neighborhood = (0, "")
    for n_norm, n in clusters["neighborhoods"]:
        sim = text_similarity(neighborhood_norm, n_norm)
        if sim > best_neighborhood[0]:
            best_neighborhood = (sim, n)

    # Find best matching zip code
    best_zip_code = (0, "")
    if cep:
        for z, _, _ in clusters["zip_codes"]:
            sim = text_similarity(cep, z)
            if sim > best_zip_code[0]:
                best_zip_code = (sim, z)
    else:
        for z in clusters["zip_codes"]:
            if address_id_ref_lat_long and z[1] == address_id_ref_lat_long:
                if best_zip_code[1] == "" or z[2] == "A":
                    best_zip_code = (1.0, z[0])

    addr_full = f"{best_street[1]}, {number}, {best_neighborhood[1]}, {city_info.city_name} - {city_info.state_code}, {best_zip_code[1]}"

    return GeoLocationResult(
        lat=lat,
        long=long,
        street_name=best_street[1],
        neighborhood=best_neighborhood[1],
        city=city_info.city_name,
        state=city_info.state_code,
        number=number,
        ref_number_lat_long=number_ref if number_ref else 0,
        zip_code=best_zip_code[1],
        address=addr_full,
    )


def geocode(
    street: str,
    neighborhood: str,
    city: str,
    state: str,
    zip_code: str | None = None,
    number: int = 0,
) -> GeoLocationResult | None:
    """
    Geocode an address to lat/long coordinates.

    Args:
        street: Street name
        neighborhood: Neighborhood name
        city: City name
        state: Two-letter state code
        zip_code: Optional 8-digit CEP
        number: Street number

    Returns:
        GeoLocationResult with coordinates and address info, or None if not found.
    """
    # Auto-download data if not present
    if not check_data_exists():
        print("Data not found. Downloading from Hugging Face...")
        download_data()

    city_info = _get_city_info(city, state)
    if not city_info:
        return None

    street_norm = normalize_text(street) if street else ""
    neighborhood_norm = normalize_text(neighborhood) if neighborhood else ""

    clean_zip = None
    if zip_code:
        clean_zip = "".join(c for c in str(zip_code) if c.isdigit()).zfill(8)

    # 1. Try CEP search first (if not multi-street), fall back to address search
    street_cluster = None
    if clean_zip and not is_multi_street_cep(clean_zip):
        street_cluster = search_by_cep(clean_zip, street_norm, neighborhood_norm)

    if not street_cluster:
        embedding = _encode_street(street_norm)
        street_cluster = _search_by_embedding(
            city_info.city_code, embedding, street_norm, neighborhood_norm
        )

    if street_cluster:
        return _build_result(
            street_cluster,
            street,
            street_norm,
            neighborhood_norm,
            clean_zip,
            number,
            city_info,
        )

    return None
```

- [ ] **Step 4: Create openaddrbr/services/_batch.py**

```python
"""Batch geocoding service - get_geo_info_batch implementation."""

from openaddrbr.core.models import AddressRequest, GeoLocationResult, NormalizedAddress
from openaddrbr.services._geocode import (
    _encode_streets_batch,
    _build_result,
    _search_by_embedding,
    _get_city_info,
    is_multi_street_cep,
    search_by_cep,
)
from openaddrbr.utils import normalize_text


def get_geo_info_batch(
    addresses: list[AddressRequest],
    batch_size: int = 16,
) -> list[GeoLocationResult | None]:
    """
    Geocode multiple addresses in batch.

    Args:
        addresses: List of AddressRequest objects
        batch_size: Number of addresses to encode in parallel

    Returns:
        List of GeoLocationResult (or None for failed lookups) in original order.
    """
    if not addresses:
        return []

    # Normalize all addresses
    normalized = [
        NormalizedAddress(
            order=i,
            address=addr,
            city_info=_get_city_info(addr.city, addr.state),
            street_norm=normalize_text(addr.street) if addr.street else "",
            neighborhood_norm=(
                normalize_text(addr.neighborhood) if addr.neighborhood else ""
            ),
            zip_code=(
                "".join(c for c in str(addr.zip_code) if c.isdigit()).zfill(8)
                if addr.zip_code
                else None
            ),
            number=addr.street_number,
        )
        for i, addr in enumerate(addresses)
    ]

    # Filter valid (has street_norm and city_info) and sort by city+street for batching
    valid = sorted(
        (n for n in normalized if n.street_norm and n.city_info),
        key=lambda n: (n.city_info.city_code, n.street_norm),
    )

    results: list[GeoLocationResult | None] = [None] * len(addresses)

    for i in range(0, len(valid), batch_size):
        batch = valid[i : i + batch_size]
        embeddings = _encode_streets_batch(
            [addr.street_norm for addr in batch], len(batch)
        )

        for addr, embedding in zip(batch, embeddings):
            cluster = None

            # Try CEP search first
            if addr.zip_code and not is_multi_street_cep(addr.zip_code):
                cluster = search_by_cep(
                    addr.zip_code, addr.street_norm, addr.neighborhood_norm
                )

            # Fall back to vector search
            if not cluster:
                street_names = []  # Need to get from vector search
                # Vector search via _search_by_embedding logic
                from openaddrbr.data import search_vector as search_vector_index

                query_ids = search_vector_index(embedding, addr.city_info.city_code, limit=20)
                if query_ids:
                    from openaddrbr.data import query_street_query, query_address_by_street_names
                    street_rows = query_street_query(query_ids, addr.city_info.city_code)
                    street_names = [row["street_normalized"] for row in street_rows]
                    if street_names:
                        clusters = _fetch_clusters_by_street_names_for_batch(
                            street_names, addr.city_info.city_code
                        )
                        if clusters:
                            from openaddrbr.utils import find_best_street_match
                            cluster = find_best_street_match(
                                clusters,
                                addr.street_norm,
                                addr.neighborhood_norm,
                                min_neighborhood_similarity=0,
                            )

            if cluster:
                results[addr.order] = _build_result(
                    cluster,
                    addr.address.street or "",
                    addr.street_norm,
                    addr.neighborhood_norm,
                    addr.zip_code,
                    addr.number,
                    addr.city_info,
                )

    return results


def _fetch_clusters_by_street_names_for_batch(street_names: list[str], city_code: int):
    """Fetch clusters for batch processing."""
    if not street_names:
        return []
    from openaddrbr.data import query_address_by_street_names
    from openaddrbr.core.models import StreetCluster

    rows = query_address_by_street_names(street_names, city_code)
    if not rows:
        return []

    clusters: list[StreetCluster] = []
    last_street_id = None
    for row in rows:
        sid = row["street_id"]
        if sid != last_street_id:
            clusters.append(StreetCluster(street_id=sid))
            last_street_id = sid
        current = clusters[-1]
        current.street_normalized.add(row["street_normalized"])
        current.neighborhood_normalized.add(row["neighborhood_normalized"])
    return clusters
```

- [ ] **Step 5: Create openaddrbr/services/__init__.py**

```python
"""Services package - business logic implementations."""

from openaddrbr.services._city import get_city_info
from openaddrbr.services._cep import search_by_cep, is_multi_street_cep
from openaddrbr.services._geocode import geocode
from openaddrbr.services._batch import get_geo_info_batch

__all__ = [
    "get_city_info",
    "search_by_cep",
    "is_multi_street_cep",
    "geocode",
    "get_geo_info_batch",
]
```

- [ ] **Step 6: Commit**

```bash
git add openaddrbr/services/
git commit -m "feat: add services (city, cep, geocode, batch)"
```

---

## Task 5: CLI - download and info commands

**Files:**
- Create: `openaddrbr/cli/_commands.py`
- Create: `openaddrbr/cli/__init__.py`

- [ ] **Step 1: Create openaddrbr/cli/_commands.py**

```python
"""CLI commands for openaddrbr."""

import argparse
import sys

from openaddrbr.data import check_data_exists, download_data, get_data_path


def _main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="openaddrbr",
        description="Brazilian address geocoder using vector search",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # download command
    download_parser = subparsers.add_parser(
        "download", help="Download data from Hugging Face"
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if data exists"
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Show data location and status")

    args = parser.parse_args()

    if args.command == "download":
        try:
            download_data(force=args.force)
        except Exception as e:
            print(f"Error downloading data: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "info":
        data_path = get_data_path()
        exists = check_data_exists()
        print(f"Data path: {data_path}")
        print(f"Data present: {'Yes' if exists else 'No'}")

    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
```

- [ ] **Step 2: Create openaddrbr/cli/__init__.py**

```python
"""CLI package."""

from openaddrbr.cli._commands import _main

__all__ = ["_main"]
```

- [ ] **Step 3: Commit**

```bash
git add openaddrbr/cli/
git commit -m "feat: add CLI commands (download, info)"
```

---

## Task 6: Main Package Init - public API

**Files:**
- Modify: `openaddrbr/__init__.py`

- [ ] **Step 1: Create openaddrbr/__init__.py**

```python
"""
OpenAddrBR - Brazilian address geocoder using vector search.

Usage:
    from openaddrbr import geocode

    result = geocode(
        street="Rua das Flores",
        neighborhood="Centro",
        city="São Paulo",
        state="SP",
        zip_code="01310000",
        number=100
    )
"""

from openaddrbr.services import get_city_info, search_by_cep, geocode, get_geo_info_batch
from openaddrbr.data import set_data_path, get_data_path, download_data

__all__ = [
    "geocode",
    "get_city_info",
    "search_by_cep",
    "get_geo_info_batch",
    "set_data_path",
    "get_data_path",
    "download_data",
]
```

- [ ] **Step 2: Commit**

```bash
git add openaddrbr/__init__.py
git commit -m "feat: expose public API in __init__.py"
```

---

## Task 7: Update Tests to work with new package structure

**Files:**
- Modify: `tests/integration/test_ibge_geocoder.py`
- Modify: `tests/unit/test_get_cod_municipio.py` → rename to `test_city.py`
- Modify: `tests/unit/test_search_by_cep.py`

- [ ] **Step 1: Update tests/integration/test_ibge_geocoder.py - change imports**

```python
# Before:
from application import IBGEGeocoder

# After:
from openaddrbr import geocode

# Or for class-based access:
# from openaddrbr.services._geocode import IBGEGeocoder  # if maintaining backward compat
```

Note: Since the new API is functional (standalone functions), the integration tests need to be rewritten to test `geocode()` function instead of `IBGEGeocoder` class. The test assertions (expected lat/long values) remain the same.

- [ ] **Step 2: Update tests/unit/test_get_cod_municipio.py → test_city.py**

```python
# Change all imports from:
from application import IBGEGeocoder
# To:
from openaddrbr.services import get_city_info
```

- [ ] **Step 3: Update tests/unit/test_search_by_cep.py - mock paths**

The mocks currently reference `application.ibge_geocoder`. Update to mock the new data module functions directly.

```python
# Before:
with patch("application.ibge_geocoder.IBGEGeocoder._get_sgeodb")

# After - mock the query functions directly:
with patch("openaddrbr.data._db.query_address_by_cep") as mock_query:
```

- [ ] **Step 4: Run tests and fix any remaining import issues**

```bash
cd d:/projetos/OpenAddrBR
source .venv/Scripts/activate  # or .venv\Scripts\activate on Windows
pip install -e .
pytest tests/ -v
```

- [ ] **Step 5: Commit**

```bash
git add tests/
git commit -m "test: update tests for new package structure"
```

---

## Task 8: Run Full Test Suite - verify all tests pass

- [ ] **Step 1: Run all tests**

```bash
pytest tests/ -v --tb=short
```

Expected: All unit and integration tests pass with same behavior as original.

- [ ] **Step 2: If tests fail, debug and fix**

Common issues:
- Import paths incorrect → fix imports
- Mock targets wrong → update mock paths
- Data path not found → ensure data path points to test data location

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "test: all tests passing"
```

---

## Self-Review Checklist

**1. Spec coverage:**
- [x] core/models - CityInfo, GeoLocation, StreetCluster, etc. ✓
- [x] core/interfaces - protocols defined ✓
- [x] data/_db.py - SQLite connection management ✓
- [x] data/_usearch.py - usearch index loading ✓
- [x] data/_hf_downloader.py - Hugging Face download ✓
- [x] data/_config.py - path configuration ✓
- [x] services/_city.py - get_city_info ✓
- [x] services/_cep.py - search_by_cep ✓
- [x] services/_geocode.py - geocode ✓
- [x] services/_batch.py - get_geo_info_batch ✓
- [x] utils/_text.py - text_to_ascii, normalize_text ✓
- [x] utils/_matching.py - text_similarity, find_best_street_match ✓
- [x] CLI - download, info commands ✓

**2. Placeholder scan:** No TBD/TODO found in plan.

**3. Type consistency:**
- CityInfo fields: city_code (int), city_name (str), state_code (str) ✓
- GeoLocationResult fields match old IBGEGeocoder output ✓
- AddressRequest fields: city, state, street, neighborhood, zip_code, street_number ✓

**Plan complete and saved to `docs/superpowers/plans/2026-05-05-openaddrbr-implementation.md`.**

---

## Execution Options

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?