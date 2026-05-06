"""Hugging Face data download manager."""

from pathlib import Path
from typing import Optional

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    HF_AVAILABLE = True
except ImportError:
    snapshot_download = None
    hf_hub_download = None
    HF_AVAILABLE = False

from openaddrbr.data._config import get_data_path, ensure_data_path, get_sgeodb_path, get_usearch_dir, get_model_path

REPO_ID = "jpsamarino/OpenAddrBR"
MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"


def download_data(
    repo_id: Optional[str] = None,
    force: bool = False,
    progress_callback=None,
) -> Path:
    """Download ALL data from Hugging Face Hub to data folder (~10GB + model)."""
    if not HF_AVAILABLE:
        raise ImportError(
            "huggingface_hub not installed. Install with: pip install huggingface_hub"
        )

    ensure_data_path()
    data_path = get_data_path()
    actual_repo = repo_id or REPO_ID

    print(f"Downloading data from Hugging Face: {actual_repo}")
    print(f"Destination: {data_path}")
    print(f"This will download ~10GB of data plus the model (~1GB). Please wait...")

    # Download everything from the repo (sgeobr.db and usearch_v2)
    snapshot_download(
        repo_id=actual_repo,
        repo_type="dataset",
        local_dir=str(data_path),
        resume_download=True,
    )

    print(f"Data downloaded successfully to {data_path}")

    # Download sentence-transformers model
    print(f"Downloading sentence-transformers model...")
    from sentence_transformers import SentenceTransformer

    model_path = get_model_path()
    if not model_path.exists() or force:
        model_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"Downloading model to {model_path}...")
        tmp_model = SentenceTransformer(MODEL_NAME)
        tmp_model.save(str(model_path))
        print(f"Model saved to {model_path}")
    else:
        print(f"Model already exists at {model_path}")

    print(f"Setup complete! All data and model are ready.")
    return data_path


def check_data_exists() -> bool:
    """Check if all required files exist (data + model)."""
    sgeodb = get_sgeodb_path()
    usearch_dir = get_usearch_dir()
    model_path = get_model_path()
    return sgeodb.exists() and usearch_dir.exists() and model_path.exists()