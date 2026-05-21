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

## Proposed Structure

```
openaddrbr/
├── __init__.py
├── __main__.py                    # allows: python -m openaddrbr
│
├── core/                          # Orchestrator (thin)
│   ├── __init__.py
│   ├── _geocoder.py                # Geocoder class, delegates to services
│   ├── _env.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── _models.py             # StreetCluster, AddressInfo, etc
│   │   └── _db_models.py          # CityRecord, AddressRecord, etc
│   └── interfaces/
│       ├── __init__.py
│       └── _protocols.py           # GeocoderDB, etc
│
├── data/                          # Data layer (all persistence)
│   ├── __init__.py
│   ├── _sql_db.py                  # SQLite wrapper (renamed from _database.py)
│   ├── _usearch.py                 # Vector index (engine explicit)
│   ├── _tantivy.py                 # Text search index (engine explicit)
│   └── _data_download.py          # HuggingFace data downloader
│
├── services/                      # Business logic (all services)
│   ├── __init__.py
│   ├── _encoder.py                 # SentenceTransformer (moved from core/)
│   ├── _result_builder.py          # _build_result, _find_best_geo_location, _NormalizedAddr
│   ├── _cep.py
│   ├── _city.py
│   ├── _vector_search.py
│   ├── _city_search.py            # uses data._tantivy
│   └── _neighborhood_search.py    # uses data._tantivy
│
└── utils/
```

## File Changes

### New Files

| File | Purpose |
|------|---------|
| `data/_tantivy.py` | Extract raw tantivy search logic (tokenizer, query builder) from `services/_city_search.py` and `services/_neighborhood_search.py` |
| `services/_result_builder.py` | Move `_build_result`, `_find_best_geo_location`, `_NormalizedAddr` from `core/_geocoder.py` |

### Renamed Files

| Old | New | Notes |
|-----|-----|-------|
| `core/_database.py` | `data/_sql_db.py` | Class `Database` → `SQLDB` |
| `data/_hf_downloader.py` | `data/_data_download.py` | Rename module and class |
| `core/_encoder.py` | `services/_encoder.py` | Move to services |

### Modified Files (no rename)

| File | Changes |
|------|---------|
| `core/_geocoder.py` | Remove `_build_result`, `_find_best_geo_location`, `_NormalizedAddr`. Import from `services._result_builder`. Import `SQLDB` from `data._sql_db`. Import `Encoder` from `services._encoder`. |
| `core/__init__.py` | Update exports |
| `core/models/__init__.py` | No change |
| `core/models/_models.py` | `_NormalizedAddr` removed (moved) |
| `core/interfaces/_protocols.py` | Review if any protocols become unused (StreetSearcher, CityFinder) |
| `services/__init__.py` | Add new exports |
| `services/_city_search.py` | Import raw tantivy logic from `data._tantivy` |
| `services/_neighborhood_search.py` | Import raw tantivy logic from `data._tantivy` |
| `data/__init__.py` | Update exports for renamed modules |
| `data/_usearch.py` | No change |

### Cleanup (if protocols are unused)

If `StreetSearcher` and `CityFinder` protocols in `core/interfaces/_protocols.py` have no consumers, remove them from:
- `core/interfaces/__init__.py`
- `core/interfaces/_protocols.py`

## Data Flow After Refactoring

```
Geocoder (core/_geocoder.py)
    ├── services/_encoder.py         # text → embedding
    ├── services/_cep.py             # CEP → StreetCluster (via data/_sql_db.py)
    ├── services/_vector_search.py   # embedding → StreetCluster (via data/_usearch.py)
    ├── services/_city_search.py     # city query → CityInfo (via data/_tantivy.py)
    ├── services/_neighborhood_search.py  # neighborhood query → NeighborhoodInfo (via data/_tantivy.py)
    └── services/_result_builder.py  # StreetCluster → AddressInfo
```

## Migration Steps

1. Create `data/_tantivy.py` with extracted raw search logic
2. Create `services/_result_builder.py` with moved helpers
3. Move `core/_encoder.py` → `services/_encoder.py`
4. Rename `core/_database.py` → `data/_sql_db.py`, class `Database` → `SQLDB`
5. Rename `data/_hf_downloader.py` → `data/_data_download.py`
6. Update `core/_geocoder.py` imports
7. Update `services/_city_search.py` and `services/_neighborhood_search.py` to use `data._tantivy`
8. Update all consumers of renamed modules
9. Clean up unused protocols if any
10. Update `__init__.py` files to export correct names

## Backward Compatibility

- `AddressInfo` remains the result type (alias `GeoLocationResult` kept for compat)
- Class name `Database` renamed to `SQLDB` — update imports in consumer code
- Module paths change — consumer code importing from `core._database` must update to `data._sql_db`

## Notes

- `_sql_db.py` naming is generic because the code uses `GeocoderDB` protocol interfaces, not the concrete class directly
- `_usearch.py` and `_tantivy.py` keep engine names explicit because consumers may need to know which engine is being used
- `core/` remains thin — it only orchestrates, all logic lives in `services/` or `data/`