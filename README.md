# OpenAddrBR

Brazilian address geocoder using vector search (usearch) + IBGE database (sgeobr.db).

**Alpha version** - For testing only. API may change.

## Installation

```bash
pip install git+https://github.com/jpsamarino/OpenAddrBR.git
```

Works on Windows, Linux, and Mac.

## Setup

```bash
# Download data (~7GB)
python -m openaddrbr download

# Auto-tune performance (runs benchmark, creates .env)
python -m openaddrbr setup
```

## Usage

### Geocoder Class (Recommended)

The `Geocoder` class provides dependency injection for testability and thread safety:

```python
from openaddrbr import Geocoder

geocoder = Geocoder()  # Model loaded into RAM (~1.3GB) immediately
result = geocoder.geocode(
    street="Rua Marcelina",
    neighborhood="Centro",
    city="Sao Paulo",
    state="SP",
)
print(result)
```

> **Model loading**: The model is loaded synchronously in `Geocoder().__init__`, reserving memory upfront. If something fails (missing data, incompatible hardware), you'll know immediately.

#### Dependency Injection

You can inject custom `Encoder` and `Database` instances for testing:

```python
from openaddrbr import Geocoder
from openaddrbr.core._encoder import Encoder
from openaddrbr.core._database import Database

# Custom configuration
geocoder = Geocoder(
    backend="onnx-int8",      # pytorch, pytorch-compiled, onnx, onnx-int8, cuda
    data_path="/custom/path", # defaults to package data
    batch_size=32,           # encoding batch size
)

# For testing: inject mocks
geocoder = Geocoder(
    encoder=MockEncoder(),
    db=MockDatabase(),
)
```

#### Batch Processing

```python
from openaddrbr import Geocoder, AddressRequest

geocoder = Geocoder()
addresses = [
    AddressRequest(street="Rua Marcelina", neighborhood="Centro", city="Sao Paulo", state="SP"),
    AddressRequest(street="Av. Brasil", neighborhood="Jardim", city="Rio de Janeiro", state="RJ"),
]
results = geocoder.geocode_batch(addresses, batch_size=16)
```

### Function API (Backwards Compatible)

For simple scripts, the function API still works:

```python
from openaddrbr import geocode

result = geocode(
    street="Rua Marcelina",
    neighborhood="Centro",
    city="Sao Paulo",
    state="SP",
)
print(result)
```

> **Note**: The function API uses a global default `Geocoder` instance internally. For production applications, use the `Geocoder` class directly for better testability and resource control.

## Return Objects

### `AddressInfo`

Returned by `geocode()` and `geocode_batch()`. Contains the geocoded address with coordinates:

```python
@dataclass
class AddressInfo:
    lat: float              # Latitude
    long: float             # Longitude
    street_name: str        # e.g., "Rua Marcelina"
    neighborhood: str       # e.g., "Centro"
    city: str               # e.g., "São Paulo"
    state: str              # e.g., "SP"
    zip_code: str           # CEP/brazilian postal code
    number: int             # Street number searched
    ref_number_lat_long: int # Reference number used for coordinates
    address: str            # Full formatted address string
```

### `CityInfo` (search API)

Returned by `geocoder.search_city()`. Contains city reference coordinates:

```python
@dataclass
class CityInfo:
    city_code: int         # IBGE city code
    city_name: str         # e.g., "São Paulo"
    city_normalized: str   # Normalized name for matching
    state_code: str        # e.g., "SP"
    latitude: float        # Reference latitude (city center)
    longitude: float        # Reference longitude (city center)
```

### `NeighborhoodInfo` (search API)

Returned by `geocoder.search_neighborhood()`. Contains neighborhood reference coordinates:

```python
@dataclass
class NeighborhoodInfo:
    neighborhood_name: str         # e.g., "Centro"
    neighborhood_normalized: str  # Normalized for matching
    city_code: int                 # IBGE city code
    latitude: float               # Reference latitude
    longitude: float              # Reference longitude
```

### `StreetInfo` (search API)

Returned by `geocoder.search_street()`. Contains street information:

```python
@dataclass
class StreetInfo:
    street_name: str             # e.g., "Rua das Flores"
    street_normalized: str      # Normalized for matching
    city_code: int              # IBGE city code
    zip_codes: list[str]        # Possible CEPs for this street
```

## Environment Variables

Create a `.env` file or set environment variables:

```bash
# Backend options: pytorch, pytorch-compiled, onnx, onnx-int8, cuda
OPENADDRBR_BACKEND=pytorch-compiled

# Batch size for encoding (default: 16)
OPENADDRBR_BATCH_SIZE=16

# Data path (default: package data directory)
OPENADDRBR_DATA_PATH=/path/to/data
```

### Backend Options

| Backend | Description |
|---------|-------------|
| `pytorch` | Plain PyTorch (no compilation) |
| `pytorch-compiled` | PyTorch + torch.compile (default, best accuracy) |
| `onnx` | ONNX float32 (no quantization) |
| `onnx-int8` | ONNX int8 (quantized, faster but may reduce accuracy) |
| `cuda` | PyTorch GPU with float16 |

Run `python -m openaddrbr setup` to auto-detect the best backend for your hardware.

## CLI Commands

```bash
python -m openaddrbr download  # Download data
python -m openaddrbr info      # Show data location
python -m openaddrbr setup     # Auto-tune performance
```

## Requirements

- Python 3.12+
- ~10GB disk space for data and model