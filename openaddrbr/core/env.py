"""Environment variable access — pure functions, no state."""

import os
from pathlib import Path

ENV_BACKEND = "OPENADDRBR_BACKEND"
ENV_DATA_PATH = "OPENADDRBR_DATA_PATH"
ENV_BATCH_SIZE = "OPENADDRBR_BATCH_SIZE"

# Module-level mutable state for data path (matches old _config behavior)
_data_path: Path | None = None
_default_data_path: Path | None = None


def get_default_data_path() -> Path:
    """Get default data path from env — caches result."""
    global _default_data_path
    if _default_data_path is None:
        env_path = os.environ.get(ENV_DATA_PATH)
        if env_path:
            _default_data_path = Path(env_path)
        else:
            _default_data_path = Path(__file__).parent.parent / "data" / "dbs"
    return _default_data_path


def get_data_path() -> Path:
    """Get the current data path (env var or custom set via set_data_path)."""
    if _data_path is not None:
        return _data_path
    return get_default_data_path()


def set_data_path(path: str | Path) -> None:
    """Set a custom data path."""
    global _data_path
    _data_path = Path(path)


def get_default_backend() -> str:
    """Get default encoder backend from env."""
    return os.environ.get(ENV_BACKEND, "pytorch")


def get_default_batch_size() -> int:
    """Get default batch size from env."""
    return int(os.environ.get(ENV_BATCH_SIZE, "16"))


def get_sgeodb_path(data_path: Path | None = None) -> Path:
    """Get path to sgeobr.db."""
    if data_path is None:
        data_path = get_default_data_path()
    return data_path / "sgeobr.db"


def get_usearch_dir(data_path: Path | None = None) -> Path:
    """Get path to usearch indices directory."""
    if data_path is None:
        data_path = get_default_data_path()
    return data_path / "usearch_v2"


def get_model_path(data_path: Path | None = None) -> Path:
    """Get path to sentence transformer model."""
    if data_path is None:
        data_path = get_default_data_path()
    return data_path / "model_paraphrase_xlmr"


def get_tantivy_dir(data_path: Path | None = None) -> Path:
    """Get path to tantivy index directory."""
    if data_path is None:
        data_path = get_default_data_path()
    return data_path / "tantivy"


def ensure_data_path(data_path: Path | None = None) -> None:
    """Ensure the data directory exists."""
    if data_path is None:
        data_path = get_default_data_path()
    data_path.mkdir(parents=True, exist_ok=True)
