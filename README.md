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

## Environment Variables

Create a `.env` file or set environment variables:

```bash
# Backend options: pytorch, pytorch-compiled, onnx, onnx-int8, cuda
OPENADDRBR_BACKEND=pytorch-compiled

# Batch size for encoding (default: 16)
OPENADDRBR_BATCH_SIZE=16
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