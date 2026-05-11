"""Environment variable access — pure functions, no state."""

import os
from pathlib import Path

ENV_BACKEND = "OPENADDRBR_BACKEND"
ENV_DATA_PATH = "OPENADDRBR_DATA_PATH"
ENV_BATCH_SIZE = "OPENADDRBR_BATCH_SIZE"


def get_default_backend() -> str:
    """Get default encoder backend from env."""
    return os.environ.get(ENV_BACKEND, "pytorch")


def get_default_data_path() -> Path:
    """Get default data path from env."""
    env_path = os.environ.get(ENV_DATA_PATH)
    if env_path:
        return Path(env_path)
    # Default: package data folder / dbs
    from pathlib import Path as _Path
    return _Path(__file__).parent.parent / "data" / "dbs"


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
