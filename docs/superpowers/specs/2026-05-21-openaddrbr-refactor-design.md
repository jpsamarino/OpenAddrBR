# Refactoring openaddrbr Package Structure

**Date:** 2026-05-21
**Status:** Draft

## Motivation

The current package structure is confusing for several reasons:

1. **`core/` is overloaded** — contains Geocoder, Database, Encoder, models, interfaces, all mixed together
2. **Database access scattered** — SQLite via `_database.py`, usearch via `data/_usearch.py`, tantivy search logic mixed in `services/`
3. **Helpers in wrong place** — `_find_best_geo_location`, `_build_result`, `_NormalizedAddr` live in `_geocoder.py` but are standalone logic
4. **Naming inconsistency** — `_database.py` is generic while `_usearch.py` and `_tantivy.py` reference specific engines

A junior developer cannot understand the architecture by looking at the folder structure.

## Performance Principle

> **Never recreate heavy objects or make unnecessary heavy system calls (like reading env vars) repeatedly.**

- Heavy objects (indexes, models, connections) must be created once and reused via lazy initialization with module-level caching
- Env vars are read once at module load, not on every call
- Use `functools.cache` only when appropriate (thread-safe, lazy), not for mutable state

## Proposed Structure

```
openaddrbr/
├── __init__.py
├── __main__.py                    # allows: python -m openaddrbr
│
├── core/                          # Orchestrator (thin)
│   ├── __init__.py
│   ├── _geocoder.py               # Geocoder class, delegates to services
│   ├── _env.py                    # env vars (read-once, no mutable state)
│   ├── models/
│   │   ├── __init__.py
│   │   ├── _models.py             # StreetCluster, AddressInfo, etc
│   │   └── _db_models.py          # CityRecord, AddressRecord, etc
│   └── interfaces/
│       ├── __init__.py
│       └── _protocols.py          # GeocoderDB, etc
│
├── data/                          # Data layer (all persistence)
│   ├── __init__.py
│   ├── _sql_db.py                 # SQLDB (SQLite wrapper, class-based)
│   ├── _usearch.py                # UsearchIndex class (vector index)
│   ├── _tantivy.py                # TantivySearch base class (text index)
│   └── _data_download.py          # HuggingFace data downloader
│
├── services/                      # Business logic (all services)
│   ├── __init__.py
│   ├── _encoder.py                # Encoder class (SentenceTransformer)
│   ├── _result_builder.py         # _build_result, _find_best_geo_location, _NormalizedAddr
│   ├── _cep.py
│   ├── _city.py
│   ├── _vector_search.py          # VectorSearch class (recebe UsearchIndex injetado)
│   ├── _city_search.py            # CitySearch class (recebe TantivySearch injetado)
│   └── _neighborhood_search.py    # NeighborhoodSearch class (recebe TantivySearch injetado)
│
└── utils/
```

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `data/_tantivy.py` | `TantivySearch` base class with raw search logic (tokenizer, query builder) — used by city and neighborhood search |
| `services/_result_builder.py` | Move `_build_result`, `_find_best_geo_location`, `_NormalizedAddr` from `core/_geocoder.py` |

### Renamed Files

| Old | New | Notes |
|-----|-----|-------|
| `core/_database.py` | `data/_sql_db.py` | Class `Database` → `SQLDB` |
| `data/_hf_downloader.py` | `data/_data_download.py` | Rename module and class |
| `core/_encoder.py` | `services/_encoder.py` | Move to services |

### Converted to Classes (no rename)

| File | Change |
|------|--------|
| `data/_usearch.py` | `get_usearch_index(city_code)` returns cached `usearch.Index` — wrapped in class for testability |
| `services/_city_search.py` | `CitySearch` class with `search(query, limit)` — receives `TantivySearch` instance injected |
| `services/_neighborhood_search.py` | `NeighborhoodSearch` class with `search(query, city_code, limit)` — receives `TantivySearch` instance injected |

### Modified Files (no rename)

| File | Changes |
|------|---------|
| `core/_geocoder.py` | Remove `_build_result`, `_find_best_geo_location`, `_NormalizedAddr`. Import from `services._result_builder`. Import `SQLDB` from `data._sql_db`. Import `Encoder` from `services._encoder`. |
| `core/__init__.py` | Update exports |
| `core/models/__init__.py` | No change |
| `core/models/_models.py` | `_NormalizedAddr` removed (moved) |
| `core/interfaces/_protocols.py` | Review if any protocols become unused (StreetSearcher, CityFinder) |
| `services/__init__.py` | Add new exports |
| `services/_vector_search.py` | Receives `UsearchIndex` instance (injected or from factory) |
| `data/__init__.py` | Update exports for renamed modules |

### Cleanup (if protocols are unused)

If `StreetSearcher` and `CityFinder` protocols in `core/interfaces/_protocols.py` have no consumers, remove them from:
- `core/interfaces/__init__.py`
- `core/interfaces/_protocols.py`

## Data Flow After Refactoring

```
Geocoder (core/_geocoder.py)
    ├── services/_encoder.py         # text → embedding
    ├── services/_cep.py             # CEP → StreetCluster (via data._sql_db)
    ├── services/_vector_search.py   # embedding → StreetCluster (via UsearchIndex)
    ├── services/_city_search.py     # city query → CityInfo (via TantivySearch)
    ├── services/_neighborhood_search.py  # neighborhood query → NeighborhoodInfo (via TantivySearch)
    └── services/_result_builder.py  # StreetCluster → AddressInfo
```

## Class Design

### `UsearchIndex` (data/_usearch.py)

```python
class UsearchIndex:
    """Thread-safe usearch index accessor with lazy initialization."""

    @staticmethod
    def get(city_code: int) -> "usearch.Index":
        """Get cached usearch index for city_code. Creates once per city_code."""
        # Caching internally, no functools.cache for testability
        ...

    @staticmethod
    def search(embedding, city_code: int, limit: int = 20) -> list[int]:
        """Search for query_ids by vector similarity."""
        ...
```

### `TantivySearch` (data/_tantivy.py)

```python
class TantivySearch:
    """Base class for tantivy text search. Handles tokenizer, query building."""

    def __init__(self, index_path: str):
        self._index = None  # lazy
        self._analyzer = ...  # built once

    def _get_index(self) -> tantivy.Index:
        """Lazy index initialization."""
        ...

    def search(self, query_text: str, field: str, city_code: int | None, limit: int) -> list[tuple]:
        """Raw search returning (score, doc_address) tuples."""
        ...
```

### `CitySearch` (services/_city_search.py)

```python
class CitySearch:
    """City autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch):
        self._ts = tantivy_search

    def search(self, query: str, limit: int = 10) -> list[CityInfo]:
        """Search cities by name."""
        ...
```

### `NeighborhoodSearch` (services/_neighborhood_search.py)

```python
class NeighborhoodSearch:
    """Neighborhood autocomplete using tantivy ngram index."""

    def __init__(self, tantivy_search: TantivySearch):
        self._ts = tantivy_search

    def search(self, query: str, city_code: int, limit: int = 10) -> list[NeighborhoodInfo]:
        """Search neighborhoods by name within city."""
        ...
```

## Migration Steps

1. Create `data/_tantivy.py` with `TantivySearch` base class
2. Create `services/_result_builder.py` with moved helpers
3. Move `core/_encoder.py` → `services/_encoder.py`
4. Rename `core/_database.py` → `data/_sql_db.py`, class `Database` → `SQLDB`
5. Rename `data/_hf_downloader.py` → `data/_data_download.py`
6. Convert `data/_usearch.py` to `UsearchIndex` class
7. Convert `services/_city_search.py` to `CitySearch` class
8. Convert `services/_neighborhood_search.py` to `NeighborhoodSearch` class
9. Update `core/_geocoder.py` imports
10. Update `services/__init__.py` exports
11. Update all consumers of renamed/converted modules
12. Clean up unused protocols if any
13. Update `__init__.py` files to export correct names

## Backward Compatibility

- `AddressInfo` remains the result type (alias `GeoLocationResult` kept for compat)
- Class name `Database` renamed to `SQLDB` — update imports in consumer code
- Module paths change — consumer code importing from `core._database` must update to `data._sql_db`
- Function-style API (`geocode()`, `get_geo_info_batch()`) remains in `__init__.py` with same signature

## Notes

- `_sql_db.py` naming is generic because the code uses `GeocoderDB` protocol interfaces, not the concrete class directly
- `_usearch.py` and `_tantivy.py` keep engine names explicit because consumers may need to know which engine is being used
- `core/` remains thin — it only orchestrates, all logic lives in `services/` or `data/`
- `_env.py` stays as-is — read-once env vars, no mutable state