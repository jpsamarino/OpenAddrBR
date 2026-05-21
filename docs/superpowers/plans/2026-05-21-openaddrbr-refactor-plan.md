# openaddrbr Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor openaddrbr package structure: move encoder to services, rename database to sql_db and convert to class-based indexes (usearch, tantivy), extract result builder, clean up protocols.

**Architecture:** `core/` becomes thin orchestrator, `data/` holds all persistence (sql_db, usearch, tantivy, download), `services/` holds all business logic (encoder, cep, city, vector, result builder).

**Tech Stack:** Python, tantivy, usearch, SQLite (apsw), sentence-transformers

---

## File Map

### Files to CREATE
- `data/_tantivy.py` — TantivySearch base class
- `services/_result_builder.py` — _build_result, _find_best_geo_location, _NormalizedAddr

### Files to RENAME
- `core/_database.py` → `data/_sql_db.py` (class `Database` → `SQLDB`)
- `data/_hf_downloader.py` → `data/_data_download.py`

### Files to MOVE
- `core/_encoder.py` → `services/_encoder.py`

### Files to CONVERT TO CLASS (no rename)
- `data/_usearch.py` → UsearchIndex class
- `services/_city_search.py` → CitySearch class
- `services/_neighborhood_search.py` → NeighborhoodSearch class

### Files to MODIFY (imports/internal only)
- `core/_geocoder.py`, `core/__init__.py`, `services/__init__.py`, `data/__init__.py`, root `__init__.py`, `__main__.py`
- `core/interfaces/_protocols.py`, `core/interfaces/__init__.py`
- Tests and benchmarks (import updates after file moves)

---

## Task 1: Create data/_tantivy.py — TantivySearch base class

Extract raw tantivy search logic (tokenizer, query builder, index loading) from `services/_city_search.py` and `services/_neighborhood_search.py` into a reusable base class.

**Files:**
- Create: `data/_tantivy.py`
- Reference: `services/_city_search.py:10-44`, `services/_neighborhood_search.py:10-57`

**Steps:**

- [ ] **Step 1: Create data/_tantivy.py with TantivySearch class**

```python
"""Tantivy text search index base class."""

import tantivy
from tantivy import Occur, TextAnalyzerBuilder, Tokenizer

from openaddrbr.core._env import get_tantivy_dir

# Ngram analyzer built once at module load
_ngram_analyzer = TextAnalyzerBuilder(Tokenizer.ngram(2, 4, prefix_only=False)).build()


class TantivySearch:
    """Base class for tantivy text search with lazy index loading."""

    def __init__(self, index_name: str):
        self._index_name = index_name
        self._index: tantivy.Index | None = None

    def _get_index(self) -> tantivy.Index:
        """Lazy index initialization — called once per instance."""
        if self._index is None:
            index_path = str(get_tantivy_dir() / self._index_name)
            self._index = tantivy.Index.open(index_path)
            self._index.register_tokenizer("ngram", _ngram_analyzer)
        return self._index

    def _build_ngram_query(
        self, query_text: str, field_name: str, schema, min_match: int | None = None
    ) -> tantivy.Query | None:
        """BooleanQuery with SHOULD (OR) per token."""
        tokens = _ngram_analyzer.analyze(query_text)
        if not tokens:
            return None

        subqueries = [(Occur.Should, tantivy.Query.term_query(schema, field_name, t)) for t in tokens]

        if min_match is None:
            n = len(tokens)
            if n <= 3:
                min_match = 1
            elif n <= 8:
                min_match = n // 2
            else:
                min_match = n // 3 * 2

        return tantivy.Query.boolean_query(subqueries, min_match)

    def search_raw(
        self, query_text: str, field_name: str, city_code: int | None = None, limit: int = 10
    ) -> list[tuple[float, int]]:
        """Raw search returning (score, doc_address) tuples.

        Args:
            query_text: Normalized query text
            field_name: Field name in tantivy schema
            city_code: Optional city_code filter
            limit: Max results

        Returns:
            List of (score, doc_address) tuples
        """
        index = self._get_index()
        searcher = index.searcher()
        schema = index.schema

        subqueries = []
        if city_code is not None:
            subqueries.append(
                (Occur.Must, tantivy.Query.term_query(schema, "city_code", city_code))
            )

        ngram_query = self._build_ngram_query(query_text, field_name, schema)
        if ngram_query is None:
            return []
        subqueries.append((Occur.Should, ngram_query))

        final_query = tantivy.Query.boolean_query(subqueries, 1)
        results = searcher.search(final_query, limit=limit)
        return [(score, doc_address) for score, doc_address in results.hits]
```

- [ ] **Step 2: Commit**

```bash
git add data/_tantivy.py
git commit -m "feat: add TantivySearch base class in data/_tantivy.py"
```

---

## Task 2: Create services/_result_builder.py

Move `_build_result`, `_find_best_geo_location`, `_NormalizedAddr` from `core/_geocoder.py`.

**Files:**
- Create: `services/_result_builder.py`
- Reference: `core/_geocoder.py:231-376`

- [ ] **Step 1: Copy helpers to services/_result_builder.py**

```python
"""Result builder — constructs AddressInfo from StreetCluster."""

from openaddrbr.core.models import StreetCluster
from openaddrbr.core.models._models import AddressInfo, CityCore, GeoLocation, GeoLocationResult
from openaddrbr.utils import normalize_text, text_similarity


class _NormalizedAddr:
    """Normalized address data used in batch processing."""
    __slots__ = ("order", "address", "city_info", "street_norm", "neighborhood_norm", "zip_code", "number")

    def __init__(self, order, address, city_info, street_norm, neighborhood_norm, zip_code, number):
        self.order = order
        self.address = address
        self.city_info = city_info
        self.street_norm = street_norm
        self.neighborhood_norm = neighborhood_norm
        self.zip_code = zip_code
        self.number = number


def _find_best_geo_location(db, street_id: int, number: int, limit_numbers: int = 3) -> GeoLocation | None:
    """Find best geo location for street_id and number with parity matching."""
    rows = db.query_geo_locations(street_id, number, limit_numbers)
    if not rows:
        return None

    ref_is_even = number % 2 == 0
    for row in rows:
        addr_num = row.address_number
        if addr_num is None:
            continue
        try:
            addr_int = int(addr_num)
        except (ValueError, TypeError):
            continue
        addr_is_even = addr_int % 2 == 0
        if ref_is_even == addr_is_even:
            return GeoLocation(
                address_id=row.address_id,
                latitude=row.latitude,
                longitude=row.longitude,
                address_number=addr_num,
            )
    # No parity match - return first
    row = rows[0]
    return GeoLocation(
        address_id=row.address_id,
        latitude=row.latitude,
        longitude=row.longitude,
        address_number=int(row.address_number),
    )


def _build_result(
    street_cluster: StreetCluster,
    street: str,
    street_norm: str,
    neighborhood_norm: str,
    cep: str | None,
    number: int,
    city_info: CityCore,
    db,
) -> AddressInfo | None:
    """Build AddressInfo from street_cluster."""
    street_id = street_cluster.street_id
    rows = db.query_full_address_by_street_id(street_id)
    if not rows:
        return None

    cluster_data = {"streets": set(), "neighborhoods": set(), "zip_codes": set()}

    for row in rows:
        if row.street_normalized in street_cluster.street_normalized:
            cluster_data["streets"].add((row.street_normalized, row.street_name))
            cluster_data["neighborhoods"].add((row.neighborhood_normalized, row.neighborhood_name))
            if row.zip_code:
                cluster_data["zip_codes"].add((str(row.zip_code).zfill(8), row.id, row.source_type))

    geo_result = _find_best_geo_location(db, street_id, number)
    if geo_result:
        lat = geo_result.latitude
        long = geo_result.longitude
        number_ref = geo_result.address_number
        address_id_ref_lat_long = geo_result.address_id
    else:
        lat, long = 0.0, 0.0
        number_ref = 0
        address_id_ref_lat_long = None

    # Find best matching street
    best_street = (0, "")
    for s_norm, s_accents in cluster_data["streets"]:
        if s_accents == street:
            best_street = (1, s_accents)
            break
        sim = text_similarity(street_norm, s_norm)
        if sim > best_street[0]:
            best_street = (sim, s_accents)

    # Find best matching neighborhood
    best_neighborhood = (0, "")
    for n_norm, n in cluster_data["neighborhoods"]:
        sim = text_similarity(neighborhood_norm, n_norm)
        if sim > best_neighborhood[0]:
            best_neighborhood = (sim, n)

    # Find best matching zip code
    best_zip_code = (0, "")
    if cep:
        for z, _, _ in cluster_data["zip_codes"]:
            sim = text_similarity(cep, z)
            if sim > best_zip_code[0]:
                best_zip_code = (sim, z)
    else:
        for z in cluster_data["zip_codes"]:
            if address_id_ref_lat_long and z[1] == address_id_ref_lat_long:
                if best_zip_code[1] == "" or z[2] == "A":
                    best_zip_code = (1.0, z[0])

    number_display = "s/n" if number == 0 else f"{number}"
    addr_full = f"{best_street[1]}, {number_display}, {best_neighborhood[1]}, {city_info.city_name} - {city_info.state_code}, {best_zip_code[1]}"

    return AddressInfo(
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
```

- [ ] **Step 2: Commit**

```bash
git add services/_result_builder.py
git commit -m "feat: extract result builder helpers to services/_result_builder.py"
```

---

## Task 3: Move core/_encoder.py → services/_encoder.py

**Files:**
- Create: `services/_encoder.py` (copy from `core/_encoder.py`)
- Modify: `core/_encoder.py` (delete after verifying)
- Modify: `benchmarks/benchmark_encoder.py:11`
- Modify: `benchmarks/benchmark_vector_search.py:15`

- [ ] **Step 1: Copy core/_encoder.py to services/_encoder.py**

```bash
cp openaddrbr/core/_encoder.py openaddrbr/services/_encoder.py
```

- [ ] **Step 2: Update import in services/__init__.py**

Add to `__all__`:
```python
from openaddrbr.services._encoder import Encoder, VALID_BACKENDS
__all__ = ["Encoder", "VALID_BACKENDS", ...]
```

- [ ] **Step 3: Verify imports in benchmarks and update**

Check `benchmarks/benchmark_encoder.py:11` and `benchmarks/benchmark_vector_search.py:15` — they import from `openaddrbr.core._encoder`. Update to:
```python
from openaddrbr.services._encoder import Encoder
```

- [ ] **Step 4: Delete core/_encoder.py and commit**

```bash
rm openaddrbr/core/_encoder.py
git add services/_encoder.py services/__init__.py
git add -u openaddrbr/core/
git commit -m "feat: move Encoder to services/"
```

---

## Task 4: Rename core/_database.py → data/_sql_db.py (class Database → SQLDB)

**Files:**
- Create: `data/_sql_db.py` (copy from `core/_database.py`)
- Modify: `core/_geocoder.py`
- Modify: `benchmarks/benchmark_usearch_memory.py:15`
- Modify: `benchmarks/benchmark_vector_search.py:14`
- Modify: `benchmarks/benchmark_db_sync.py:26`

- [ ] **Step 1: Copy and rename class**

```bash
cp openaddrbr/core/_database.py openaddrbr/data/_sql_db.py
```

In `data/_sql_db.py`, rename class `Database` → `SQLDB`.

- [ ] **Step 2: Update imports in core/_geocoder.py**

Change:
```python
from openaddrbr.core._database import Database
```
to:
```python
from openaddrbr.data._sql_db import SQLDB
```

Also update `self.db = db if db is not None else Database(...)` to `self.db = db if db is not None else SQLDB(...)`.

- [ ] **Step 3: Update core/__init__.py**

Change `Database` → `SQLDB` in exports.

- [ ] **Step 4: Update benchmark imports**

Update the 3 benchmark files to import from `data._sql_db`.

- [ ] **Step 5: Delete core/_database.py and commit**

```bash
rm openaddrbr/core/_database.py
git add data/_sql_db.py core/__init__.py core/_geocoder.py
git add -u benchmarks/
git add -u openaddrbr/core/
git commit -m "refactor: rename Database to SQLDB and move to data/"
```

---

## Task 5: Rename data/_hf_downloader.py → data/_data_download.py

**Files:**
- Rename: `data/_hf_downloader.py` → `data/_data_download.py`
- Modify: `data/__init__.py`
- Modify: Any consumer imports

- [ ] **Step 1: Rename file**

```bash
mv openaddrbr/data/_hf_downloader.py openaddrbr/data/_data_download.py
```

- [ ] **Step 2: Update data/__init__.py**

```python
from openaddrbr.data._data_download import check_data_exists, download_data
```

- [ ] **Step 3: Commit**

```bash
git add -u openaddrbr/data/
git commit -m "refactor: rename _hf_downloader to _data_download"
```

---

## Task 6: Convert data/_usearch.py to UsearchIndex class

**Files:**
- Modify: `data/_usearch.py`
- Modify: `services/_vector_search.py`
- Modify: `benchmarks/benchmark_usearch_memory.py:17`

- [ ] **Step 1: Rewrite data/_usearch.py as UsearchIndex class**

```python
"""Usearch vector index — thread-safe with lazy initialization."""

from functools import lru_cache
from pathlib import Path

import numpy as np

try:
    from usearch.index import Index as usearch_Index
except ImportError:
    usearch_Index = None

from openaddrbr.core._env import get_usearch_dir


class UsearchIndex:
    """Thread-safe usearch index accessor with lazy initialization per city_code."""

    _cache: dict[int, "usearch_Index"] = {}

    @classmethod
    def get(cls, city_code: int) -> "usearch_Index | None":
        """Get cached usearch index for city_code. Creates once per city_code."""
        if cls._cache.get(city_code) is None:
            if usearch_Index is None:
                return None
            index_path = get_usearch_dir() / f"{city_code}.usearch"
            if not index_path.exists():
                cls._cache[city_code] = None
                return None
            cls._cache[city_code] = usearch_Index(path=str(index_path), view=True)
        return cls._cache[city_code]

    @classmethod
    def search(cls, embedding, city_code: int, limit: int = 20) -> list[int]:
        """Search for query_ids by vector similarity."""
        index = cls.get(city_code)
        if index is None:
            return []
        results = index.search(embedding.astype(np.float32), count=limit)
        return [int(r.key) for r in results]

    @classmethod
    def clear_cache(cls) -> None:
        """Clear index cache — for testing only."""
        cls._cache.clear()
```

- [ ] **Step 2: Update services/_vector_search.py**

Change:
```python
from openaddrbr.data import search_vector as search_vector_index
```
to:
```python
from openaddrbr.data._usearch import UsearchIndex
```
And replace `search_vector_index(...)` with `UsearchIndex.search(...)`.

- [ ] **Step 3: Update benchmark_usearch_memory.py:17**

```python
from openaddrbr.data._usearch import UsearchIndex
```

- [ ] **Step 4: Update data/__init__.py**

Remove `get_semantic_index` and `search_vector` from exports (internal now), keep `_usearch` available.

- [ ] **Step 5: Commit**

```bash
git add data/_usearch.py services/_vector_search.py benchmarks/benchmark_usearch_memory.py data/__init__.py
git commit -m "refactor: convert _usearch to UsearchIndex class"
```

---

## Task 7: Convert services/_city_search.py to CitySearch class

**Files:**
- Modify: `services/_city_search.py`
- Modify: `core/_geocoder.py` (search_city method)
- Modify: `benchmarks/benchmark_city_autocomplete.py:11`

- [ ] **Step 1: Rewrite services/_city_search.py as CitySearch class**

```python
"""City autocomplete using Tantivy ngram index."""

from openaddrbr.core._env import get_tantivy_dir
from openaddrbr.core.models import CityInfo
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.utils import normalize_text


class CitySearch:
    """City autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch | None = None):
        self._ts = tantivy_search or TantivySearch("city_index")

    def search(self, query: str, limit: int = 10) -> list[CityInfo]:
        """Search for cities by name using ngram autocomplete."""
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._ts.search_raw(query_normalized, "city_search", city_code=None, limit=limit)
        if not hits:
            return []

        index = self._ts._get_index()
        searcher = index.searcher()

        cities = []
        for score, doc_address in hits:
            doc = searcher.doc(doc_address)
            city_name = doc.get_first("city_name") or ""
            cities.append(
                CityInfo(
                    city_code=doc.get_first("city_code"),
                    city_name=city_name,
                    city_normalized=normalize_text(city_name),
                    state_code=doc.get_first("state_code"),
                    latitude=doc.get_first("ref_latitude"),
                    longitude=doc.get_first("ref_longitude"),
                )
            )
        return cities
```

- [ ] **Step 2: Update core/_geocoder.py search_city method**

```python
def search_city(self, query: str, limit: int = 10) -> list[CityInfo]:
    from openaddrbr.services._city_search import CitySearch
    return CitySearch().search(query, limit)
```

- [ ] **Step 3: Update benchmark_city_autocomplete.py**

Update import to use new class or keep using `search_city_tantivy` function (keep function wrapper for backward compat).

- [ ] **Step 4: Update services/__init__.py**

```python
from openaddrbr.services._city_search import CitySearch
__all__ = [..., "CitySearch"]
```

- [ ] **Step 5: Commit**

```bash
git add services/_city_search.py core/_geocoder.py benchmarks/benchmark_city_autocomplete.py services/__init__.py
git commit -m "refactor: convert _city_search to CitySearch class"
```

---

## Task 8: Convert services/_neighborhood_search.py to NeighborhoodSearch class

**Files:**
- Modify: `services/_neighborhood_search.py`
- Modify: `core/_geocoder.py` (search_neighborhood method)
- Modify: `benchmarks/benchmark_neighborhood_autocomplete.py:11-12`

- [ ] **Step 1: Rewrite services/_neighborhood_search.py as NeighborhoodSearch class**

```python
"""Neighborhood autocomplete using Tantivy ngram index."""

from openaddrbr.core.models import NeighborhoodInfo
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.utils import normalize_text


class NeighborhoodSearch:
    """Neighborhood autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch | None = None):
        self._ts = tantivy_search or TantivySearch("neighborhood_index")

    def search(self, query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
        """Search for neighborhoods by name within city."""
        query_normalized = normalize_text(query)
        if not query_normalized:
            return []

        hits = self._ts.search_raw(query_normalized, "neighborhood_search", city_code=city_code, limit=limit)
        if not hits:
            return []

        index = self._ts._get_index()
        searcher = index.searcher()

        neighborhoods = []
        for score, doc_address in hits:
            doc = searcher.doc(doc_address)
            neighborhood_name = doc.get_first("neighborhood_name") or ""
            neighborhoods.append(
                NeighborhoodInfo(
                    neighborhood_name=neighborhood_name,
                    neighborhood_normalized=normalize_text(neighborhood_name),
                    city_code=doc.get_first("city_code"),
                    latitude=doc.get_first("ref_latitude"),
                    longitude=doc.get_first("ref_longitude"),
                )
            )
        return neighborhoods
```

- [ ] **Step 2: Update core/_geocoder.py search_neighborhood method**

```python
def search_neighborhood(self, query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
    from openaddrbr.services._neighborhood_search import NeighborhoodSearch
    return NeighborhoodSearch().search(query, city_code, limit)
```

- [ ] **Step 3: Update benchmark_neighborhood_autocomplete.py**

Update import.

- [ ] **Step 4: Update services/__init__.py**

```python
from openaddrbr.services._neighborhood_search import NeighborhoodSearch
__all__ = [..., "NeighborhoodSearch"]
```

- [ ] **Step 5: Commit**

```bash
git add services/_neighborhood_search.py core/_geocoder.py benchmarks/benchmark_neighborhood_autocomplete.py services/__init__.py
git commit -m "refactor: convert _neighborhood_search to NeighborhoodSearch class"
```

---

## Task 9: Update core/_geocoder.py — remove helpers, update all imports

Clean up `_geocoder.py` to import helpers from services and remove local definitions.

**Files:**
- Modify: `core/_geocoder.py`
- Reference: `services/_result_builder.py`

- [ ] **Step 1: Update imports in core/_geocoder.py**

Remove:
- `normalize_text`, `text_similarity` (keep only if still used, otherwise use from services)
- `_find_best_geo_location`, `_build_result`, `_NormalizedAddr` (now in services)

Add:
```python
from openaddrbr.services._encoder import Encoder
from openaddrbr.services._result_builder import _build_result, _NormalizedAddr
from openaddrbr.services._cep import is_multi_street_cep, search_by_cep
from openaddrbr.services._vector_search import search_by_embedding
from openaddrbr.data._sql_db import SQLDB
```

- [ ] **Step 2: Remove local definitions of `_build_result`, `_find_best_geo_location`, `_NormalizedAddr`**

Delete lines 231-376 approximately.

- [ ] **Step 3: Verify all imports are correct**

Run a quick syntax check:
```bash
python -c "import openaddrbr.core._geocoder; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add core/_geocoder.py
git commit -m "refactor: clean up _geocoder.py, import helpers from services"
```

---

## Task 10: Update all __init__.py files and protocols

**Files:**
- Modify: `core/__init__.py`, `services/__init__.py`, `data/__init__.py`, root `__init__.py`
- Modify: `core/interfaces/__init__.py`, `core/interfaces/_protocols.py`

- [ ] **Step 1: Update core/__init__.py**

```python
from openaddrbr.core._geocoder import Geocoder
from openaddrbr.data._sql_db import SQLDB

__all__ = ["Geocoder", "SQLDB"]
```

- [ ] **Step 2: Update services/__init__.py**

```python
from openaddrbr.services._encoder import Encoder
from openaddrbr.services._cep import is_multi_street_cep, search_by_cep
from openaddrbr.services._city import get_city_info
from openaddrbr.services._city_search import CitySearch
from openaddrbr.services._neighborhood_search import NeighborhoodSearch
from openaddrbr.services._vector_search import search_by_embedding
from openaddrbr.services._result_builder import _build_result, _NormalizedAddr

__all__ = [
    "Encoder",
    "get_city_info",
    "search_by_cep",
    "is_multi_street_cep",
    "CitySearch",
    "NeighborhoodSearch",
    "search_by_embedding",
    "_build_result",
    "_NormalizedAddr",
]
```

- [ ] **Step 3: Update data/__init__.py**

```python
from openaddrbr.data._sql_db import SQLDB
from openaddrbr.data._usearch import UsearchIndex
from openaddrbr.data._tantivy import TantivySearch
from openaddrbr.data._data_download import check_data_exists, download_data
from openaddrbr.core._env import get_data_path, get_sgeodb_path, get_usearch_dir, set_data_path

__all__ = [
    "SQLDB",
    "UsearchIndex",
    "TantivySearch",
    "check_data_exists",
    "download_data",
    "get_data_path",
    "set_data_path",
    "get_sgeodb_path",
    "get_usearch_dir",
]
```

- [ ] **Step 4: Update root __init__.py**

```python
from openaddrbr.core._geocoder import Geocoder
from openaddrbr.core.models import AddressInfo, AddressRequest, CityInfo, NeighborhoodInfo

__all__ = ["Geocoder", "geocode", "get_geo_info_batch", "NeighborhoodInfo", "AddressInfo", "AddressRequest", "CityInfo"]

# Lazy-initialized default geocoder instance for backwards-compatible function API
_default_geocoder: Geocoder | None = None

def geocode(...): ...  # unchanged
def get_geo_info_batch(...): ...  # unchanged
```

- [ ] **Step 5: Clean up protocols — check if StreetSearcher/CityFinder are used**

```bash
grep -r "StreetSearcher\|CityFinder" openaddrbr/ --include="*.py"
```

If no usage, remove from `core/interfaces/_protocols.py` and `core/interfaces/__init__.py`.

- [ ] **Step 6: Commit**

```bash
git add core/__init__.py services/__init__.py data/__init__.py openaddrbr/__init__.py core/interfaces/
git commit -m "refactor: update all package exports and clean up protocols"
```

---

## Task 11: Create __main__.py for python -m openaddrbr

**Files:**
- Create: `openaddrbr/__main__.py`

- [ ] **Step 1: Create __main__.py**

Check existing CLI in `openaddrbr/cli/__init__.py` for what to call:

```python
"""Allow: python -m openaddrbr"""
from openaddrbr.cli import _main

if __name__ == "__main__":
    _main()
```

- [ ] **Step 2: Commit**

```bash
git add openaddrbr/__main__.py
git commit -m "feat: add __main__.py for python -m openaddrbr"
```

---

## Task 12: Fix broken tests after restructuring

**Files:**
- Modify: `tests/unit/test_database.py`, `tests/unit/test_encoder.py`, `tests/unit/test_services.py`, `tests/unit/test_geocoder.py`
- Modify: `tests/integration/test_city_search.py`, `tests/integration/test_neighborhood_search.py`

- [ ] **Step 1: Update test_database.py imports**

```python
# Before:
from openaddrbr.core._database import CityRecord, Database
# After:
from openaddrbr.data._sql_db import CityRecord, SQLDB
```

- [ ] **Step 2: Update test_encoder.py imports**

```python
# Before:
from openaddrbr.core._encoder import VALID_BACKENDS, Encoder
# After:
from openaddrbr.services._encoder import VALID_BACKENDS, Encoder
```

- [ ] **Step 3: Update test_services.py**

Check for `CityRecord` import from old path. Update to new.

- [ ] **Step 4: Update test_geocoder.py**

Check `from openaddrbr.core._geocoder import Geocoder` — should still work, but check internals.

- [ ] **Step 5: Update integration tests**

Check `test_city_search.py` and `test_neighborhood_search.py` imports — update to use new classes.

- [ ] **Step 6: Run tests**

```bash
pytest tests/unit/ -v --tb=short 2>&1 | head -100
```

Fix any remaining import failures.

- [ ] **Step 7: Commit**

```bash
git add -u tests/
git commit -m "test: fix imports after restructuring"
```

---

## Task 13: Fix broken benchmarks after restructuring

**Files:**
- Modify: `benchmarks/benchmark_usearch_memory.py`, `benchmarks/benchmark_vector_search.py`, `benchmarks/benchmark_db_sync.py`, `benchmarks/benchmark_encoder.py`, `benchmarks/benchmark_city_autocomplete.py`, `benchmarks/benchmark_neighborhood_autocomplete.py`

- [ ] **Step 1: Update benchmark_usearch_memory.py imports**

```python
# Before:
from openaddrbr.core._database import Database
from openaddrbr.data._usearch import get_semantic_index
# After:
from openaddrbr.data._sql_db import SQLDB
from openaddrbr.data._usearch import UsearchIndex
```

- [ ] **Step 2: Update benchmark_vector_search.py imports**

```python
# Before:
from openaddrbr.core._database import Database
from openaddrbr.core._encoder import Encoder
# After:
from openaddrbr.data._sql_db import SQLDB
from openaddrbr.services._encoder import Encoder
```

- [ ] **Step 3: Update benchmark_db_sync.py import**

```python
# Before:
from openaddrbr.core._database import Database
# After:
from openaddrbr.data._sql_db import SQLDB
```

- [ ] **Step 4: Update benchmark_encoder.py import**

```python
# Before:
from openaddrbr.core._encoder import Encoder
# After:
from openaddrbr.services._encoder import Encoder
```

- [ ] **Step 5: Update benchmark_city_autocomplete.py**

```python
# Before:
from openaddrbr.services._city_search import search_city_tantivy
# After (if keeping function wrapper):
# Keep the function, just update internal import in _city_search.py
```

- [ ] **Step 6: Update benchmark_neighborhood_autocomplete.py**

```python
# Before:
from openaddrbr.services._neighborhood_search import search_neighborhood_tantivy
# After (if keeping function wrapper):
# Keep the function, just update internal import
```

- [ ] **Step 7: Run a quick benchmark to verify**

```bash
python -m benchmarks.benchmark_encoder
```

- [ ] **Step 8: Commit**

```bash
git add -u benchmarks/
git commit -m "benchmark: fix imports after restructuring"
```

---

## Task 14: Benchmark comparison report — main vs refactored

**Goal:** Run each benchmark 2× on `main` and 2× on the refactored branch, produce a comparison report.

**Benchmarks to compare:**
- `benchmarks/benchmark_encoder.py` — Encoder throughput (ms/text)
- `benchmarks/benchmark_vector_search.py` — Vector search latency (ms/query)
- `benchmarks/benchmark_city_autocomplete.py` — City search latency (ms/query)
- `benchmarks/benchmark_neighborhood_autocomplete.py` — Neighborhood search latency (ms/query)
- `benchmarks/benchmark_usearch_memory.py` — Memory usage check
- `benchmarks/benchmark_api_comparison.py` — End-to-end geocoding latency
- `benchmarks/benchmark_db_sync.py` — DB query latency

**Files:**
- Create: `docs/superpowers/plans/2026-05-21-benchmark-comparison-report.md`

- [ ] **Step 1: On main branch, stash any pending changes and ensure clean state**

```bash
git stash
git checkout main
```

- [ ] **Step 2: Run benchmarks on main — 2 runs each, record results**

Run each benchmark twice, capture timing output. Example for encoder:

```bash
# Run 1
python -m benchmarks.benchmark_encoder 2>&1 | tee /tmp/encoder_main_run1.txt
# Run 2
python -m benchmarks.benchmark_encoder 2>&1 | tee /tmp/encoder_main_run2.txt
```

Repeat for all benchmarks. Store results in `/tmp/benchmark_main_*.txt`.

- [ ] **Step 3: Checkout refactored branch**

```bash
git checkout -
# or git checkout refactor-branch-name
```

- [ ] **Step 4: Run benchmarks on refactored branch — 2 runs each, record results**

Same as Step 2, store in `/tmp/benchmark_refactored_*.txt`.

- [ ] **Step 5: Create comparison report**

Create `docs/superpowers/plans/2026-05-21-benchmark-comparison-report.md` with:

```markdown
# Benchmark Comparison Report

**Date:** 2026-05-21
**Baseline:** main branch (before refactoring)
**Comparison:** refactored branch (after restructuring)

## Methodology

Each benchmark run twice. Results shown as: mean ± stddev.
Latency in ms, throughput in items/sec, memory in MB.

## Results

| Benchmark | Metric | main (run1) | main (run2) | refactored (run1) | refactored (run2) | Δ% |
|-----------|--------|-------------|-------------|-------------------|-------------------|-----|
| benchmark_encoder | ms/text | X | X | X | X | ±Y% |
| benchmark_vector_search | ms/query | X | X | X | X | ±Y% |
| benchmark_city_autocomplete | ms/query | X | X | X | X | ±Y% |
| benchmark_neighborhood_autocomplete | ms/query | X | X | X | X | ±Y% |
| benchmark_api_comparison | ms/geocode | X | X | X | X | ±Y% |
| benchmark_db_sync | ms/query | X | X | X | X | ±Y% |

## Analysis

### Items that improved:
- (list with explanation)

### Items that regressed:
- (list with explanation and root cause)

### Items with no significant change:
- (list)

## Root Cause Analysis

For each regression, investigate:
1. Extra import overhead (new module resolution)
2. Class instantiation overhead vs function calls
3. Caching behavior differences (global vs class)
4. Any algorithmic changes

## Recommendations

- (actionable items to fix regressions, if any)
```

- [ ] **Step 6: Commit comparison report**

```bash
git add docs/superpowers/plans/2026-05-21-benchmark-comparison-report.md
git commit -m "docs: add benchmark comparison report main vs refactored"
```

---

## Task 15: Final verification — run full test suite

**Files:**
- Run: all tests and benchmarks

- [ ] **Step 1: Run all unit tests**

```bash
pytest tests/unit/ -v --tb=short 2>&1 | tail -30
```

- [ ] **Step 2: Run integration tests**

```bash
pytest tests/integration/ -v --tb=short 2>&1 | tail -30
```

- [ ] **Step 3: Verify imports work at top level**

```bash
python -c "from openaddrbr import Geocoder, geocode, CitySearch, NeighborhoodSearch, UsearchIndex, SQLDB; print('All imports OK')"
```

- [ ] **Step 4: Commit final state**

```bash
git add -A
git commit -m "chore: complete refactoring — restructured core/data/services"
```

---

## Task Order Summary

1. **data/_tantivy.py** — TantivySearch base class
2. **services/_result_builder.py** — extract helpers
3. **services/_encoder.py** — move from core/
4. **data/_sql_db.py** — rename from core/_database.py, Database → SQLDB
5. **data/_data_download.py** — rename from _hf_downloader.py
6. **data/_usearch.py** — convert to UsearchIndex class
7. **services/_city_search.py** — convert to CitySearch class
8. **services/_neighborhood_search.py** — convert to NeighborhoodSearch class
9. **core/_geocoder.py** — remove helpers, update all imports
10. **All __init__.py** — update exports and protocols
11. **__main__.py** — create for `python -m openaddrbr`
12. **tests/** — fix broken imports
13. **benchmarks/** — fix broken imports
14. **Benchmark comparison report** — main vs refactored, 2× runs each
15. **Final verification** — run full test suite