# Geocoder Class DI Refactoring — Design

## Motivation

- **Thread safety**: Globals (`_model`, `_db_instance`) are unsafe across threads
- **Testability**: Cannot mock encoder/DB in unit tests without hacks
- **Breaking change to 1.0**: Justified for this architectural shift

## Goals

1. Replace module-level globals with classes
2. Keep it lightweight — no DI containers, no factories beyond simple constructors
3. Maintain performance — no unnecessary abstraction layers
4. Env vars remain the way to configure defaults
5. **Max 400 lines per file** — split larger classes into composables

## Components

### `Geocoder`

Main entry point. Holds instances of `Encoder` and `Database`.

```python
class Geocoder:
    def __init__(
        self,
        backend: str | None = None,
        data_path: str | Path | None = None,
        batch_size: int | None = None,
    ):
        self.encoder = Encoder(backend=backend)
        self.db = Database(data_path=data_path)
        self.batch_size = batch_size or int(env("OPENADDRBR_BATCH_SIZE", 16))

    def geocode(self, street, neighborhood, city, state, zip_code=None, number=0) -> GeoLocationResult | None
    def geocode_batch(self, addresses: list[AddressRequest]) -> list[GeoLocationResult | None]
```

### `Encoder`

Wraps `SentenceTransformer`. Handles backend selection and model lifecycle.

```python
class Encoder:
    def __init__(self, backend: str | None = None):
        self.backend = backend or env("OPENADDRBR_BACKEND", "pytorch")
        self._model: SentenceTransformer | None = None

    def encode(self, text: str) -> np.ndarray
    def encode_batch(self, texts: list[str], batch_size: int | None = None) -> list[np.ndarray]
```

### `Database`

Thread-safe connection pool. Query methods become instance methods.

```python
class Database:
    def __init__(self, data_path: str | Path | None = None):
        self._data_path = data_path or env("OPENADDRBR_DATA_PATH", DEFAULT_DATA_DIR)
        self._lock = threading.Lock()
        self._cursors: dict[int, apsw.Cursor] = {}

    def query_geo_locations(self, street_id, number, limit=3) -> list[GeoInfoRecord]
    def query_full_address_by_street_id(self, street_id) -> list[FullAddressRecord]
    # ... all other query methods
```

### Environment Config

Pure module with env var access — no state.

```python
# openaddrbr/data/_config.py
ENV_BACKEND = "OPENADDRBR_BACKEND"
ENV_DATA_PATH = "OPENADDRBR_DATA_PATH"
ENV_BATCH_SIZE = "OPENADDRBR_BATCH_SIZE"

def get_default_backend() -> str: ...
def get_default_data_path() -> Path: ...
def get_default_batch_size() -> int: ...
```

### Pure Utility Functions (unchanged)

```python
normalize_text(text: str) -> str
text_similarity(a: str, b: str) -> float
find_best_street_match(...) -> StreetCluster | None
```

## API Change

### Before
```python
from openaddrbr import geocode
result = geocode(street="Rua X", city="São Paulo", state="SP")
```

### After
```python
from openaddrbr import Geocoder
geocoder = Geocoder()
result = geocoder.geocode(street="Rua X", city="São Paulo", state="SP")
```

**Breaking change**: `geocode()` function is removed from public API.

## Data Flow

```
Geocoder.geocode(street, city, state, ...)
  ├── Encoder.encode(street_norm) → embedding
  ├── Database.query_* → records
  └── builds GeoLocationResult
```

No circular dependencies. `Database` is stateless (connection pool only). `Encoder` loads model lazily.

## Thread Safety

- `Encoder`: Model is loaded once, shared read-only across threads. Safe if no `torch.compile` is triggered concurrently.
- `Database`: Per-thread cursors via `threading.get_ident()`. Existing pattern preserved.

## Performance Considerations

- **No additional indirection**: Direct method calls, no factory lookup
- **Lazy loading**: Model loaded only on first encode, not at `Geocoder()` construction
- **Connection pooling**: Already exists in `_DB`, preserved
- **Batch encoding**: `Encoder.encode_batch` calls model once with list

## Backward Compatibility

None. This is a 1.0 release.

## Files to Change

### New Files
- `openaddrbr/core/_geocoder.py` — `Geocoder` class
- `openaddrbr/core/_encoder.py` — `Encoder` class (refactored from `services/_encoder.py`)
- `openaddrbr/core/_database.py` — `Database` class (refactored from `data/_db.py`)

### Modified Files
- `openaddrbr/__init__.py` — export only `Geocoder`
- `openaddrbr/data/_config.py` — extract env var logic, remove globals
- `openaddrbr/services/_geocode.py` — move logic into `Geocoder`
- `openaddrbr/services/_batch.py` — move into `Geocoder.geocode_batch`
- `openaddrbr/services/_vector_search.py` — becomes standalone (Encoder/DB passed in)
- `openaddrbr/data/__init__.py` — export `Database`
- All test files — rewrite with `Geocoder(encoder=MockEncoder(), db=MockDatabase())`

### Deleted Files
- `openaddrbr/services/_encoder.py` — merged into `Encoder`
- `openaddrbr/data/_db.py` — merged into `Database`

## Implementation Order

1. Extract `_config.py` env logic (no dependencies)
2. Create `Encoder` class
3. Create `Database` class
4. Create `Geocoder` class composing both
5. Rewrite tests
6. Update benchmarks
7. Release 1.0

## Open Decisions (RESOLVED)

- **async**: No async support for 1.0
- **context manager**: Optional, not required, no cleanup needed
- **search_by_cep**: Moves into `Geocoder` as method
- **cache strategy**: Use `cachetools.LRUCache` for bounded memory caches inside `Database`
- **shared Database**: Yes — `Geocoder(db=shared_db)` pattern for tests only; users typically use single instance

## Database Caching

Bounded caches inside `Database` using `cachetools.LRUCache`:

```python
from cachetools import LRUCache

class Database:
    def __init__(self, data_path: str | Path | None = None):
        self._city_cache = LRUCache(maxsize=7000)
        self._multi_street_cache = LRUCache(maxsize=10000)
        self._street_query_cache = LRUCache(maxsize=5000)
        # ...
```

Why: Python dict has no memory limit. `cachetools` is lightweight, standard in ML projects.

**Dependency**: Add `cachetools>=5.3` to `pyproject.toml`/`setup.py`.
