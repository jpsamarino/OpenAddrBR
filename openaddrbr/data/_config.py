"""Data path configuration management."""

import os
from pathlib import Path
from typing import Optional

# Environment variable for data path override
ENV_DATA_PATH = "OPENADDRBR_DATA_PATH"

# Default data directory (inside package data folder, named dbs)
DEFAULT_DATA_DIR = Path(__file__).parent / "dbs"

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
