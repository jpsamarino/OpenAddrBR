"""Hugging Face data download manager."""

from pathlib import Path
from typing import Optional

try:
    from huggingface_hub import snapshot_download
    HF_AVAILABLE = True
except ImportError:
    snapshot_download = None
    HF_AVAILABLE = False

from openaddrbr.data._config import get_data_path, ensure_data_path, get_sgeodb_path, get_usearch_dir

REPO_ID = "your-org/openaddrbr-data"  # Placeholder - update to actual repo


def download_data(
    repo_id: Optional[str] = None,
    force: bool = False,
    progress_callback=None,
) -> Path:
    """Download data from Hugging Face Hub."""
    if not HF_AVAILABLE:
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
    sgeodb = get_sgeodb_path()
    usearch_dir = get_usearch_dir()
    return sgeodb.exists() and usearch_dir.exists()