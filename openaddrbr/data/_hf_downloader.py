"""Hugging Face data download manager."""

import os
import sys
import tarfile
import zstandard as zstd
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

COMPRESSED_SGEEBR_DB = "sgeobr.db.tar.zst"
COMPRESSED_USEARCH = "usearch_v2.tar.zst"


def _print(msg: str) -> None:
    """Print message to stderr to avoid polluting stdout (which may be captured)."""
    print(msg, file=sys.stderr)


def _get_remote_compressed_files() -> dict[str, str]:
    """List .tar.zst files that exist in the remote HF repository."""
    from huggingface_hub import list_repo_files
    try:
        files = list_repo_files(repo_id=REPO_ID, repo_type="dataset", token=os.environ.get("HF_TOKEN"))
        result = {}
        for f in files:
            if f.endswith(".tar.zst"):
                result[f] = f  # key == value for now, maps remote name to local target
        return result
    except Exception:
        return {}


def _download_compressed_file(filename: str, dest_dir: Path, force: bool = False) -> Path:
    """Download a single .tar.zst file from HF and return local path."""
    from huggingface_hub import hf_hub_download

    local_path = dest_dir / filename
    if local_path.exists() and not force:
        return local_path

    token = os.environ.get("HF_TOKEN")
    downloaded = hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        repo_type="dataset",
        local_dir=str(dest_dir),
        token=token,
    )
    return Path(downloaded)


def _extract_tar_zst(tar_path: Path, dest_dir: Path, remove_after: bool = True) -> None:
    """Extract a .tar.zst file using zstandard + tarfile."""
    _print(f"[OpenAddrBR] Extracting {tar_path.name}...")

    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".tar", delete=False) as tmp_tar:
        tmp_tar_path = tmp_tar.name

    try:
        with open(tar_path, "rb") as compressed:
            dctx = zstd.ZstdDecompressor()
            with open(tmp_tar_path, "wb") as decompressed:
                dctx.copy_stream(compressed, decompressed)

        with tarfile.open(tmp_tar_path, "r") as tar:
            tar.extractall(path=dest_dir)

        _print(f"[OpenAddrBR] Extracted: {tar_path.name}")
    finally:
        import os as _os
        _os.unlink(tmp_tar_path)
        if remove_after:
            tar_path.unlink()


def _get_missing_items() -> list[str]:
    """Check what's missing and return list of missing items."""
    missing = []
    if not get_sgeodb_path().exists():
        missing.append("sgeobr.db")
    if not get_usearch_dir().exists():
        missing.append("usearch_v2/")
    if not get_model_path().exists():
        missing.append("model_paraphrase_xlmr/")
    return missing


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

    data_path = get_data_path()
    actual_repo = repo_id or REPO_ID

    _print(f"[OpenAddrBR] Data path: {data_path}")

    # Check what's missing
    missing = _get_missing_items()

    if not missing and not force:
        _print(f"[OpenAddrBR] All data already exists! Nothing to download.")
        return data_path

    if missing:
        _print(f"[OpenAddrBR] Missing: {', '.join(missing)}")

    ensure_data_path()

    # Download from HuggingFace (handles resume automatically)
    _print(f"[OpenAddrBR] Downloading data from Hugging Face: {actual_repo}")
    _print(f"[OpenAddrBR] Destination: {data_path}")
    _print(f"[OpenAddrBR] HF will download only missing files (resume support)...")

    # Suppress huggingface_hub stdout noise by redirecting to stderr
    old_stdout = sys.stdout
    sys.stdout = sys.stderr

    # Get HF token if available (for higher rate limits on paid accounts)
    hf_token = os.environ.get("HF_TOKEN")

    try:
        snapshot_download(
            repo_id=actual_repo,
            repo_type="dataset",
            local_dir=str(data_path),
            resume_download=True,
            max_workers=2,
            token=hf_token,
        )
    finally:
        sys.stdout = old_stdout

    _print(f"[OpenAddrBR] HF data downloaded to {data_path}")

    # Download sentence-transformers model
    model_path = get_model_path()
    if not model_path.exists() or force:
        _print(f"[OpenAddrBR] Downloading sentence-transformers model...")
        from sentence_transformers import SentenceTransformer

        model_path.parent.mkdir(parents=True, exist_ok=True)
        _print(f"[OpenAddrBR] Downloading model to {model_path}...")
        tmp_model = SentenceTransformer(MODEL_NAME)
        tmp_model.save(str(model_path))
        _print(f"[OpenAddrBR] Model saved to {model_path}")
    else:
        _print(f"[OpenAddrBR] Model already exists at {model_path}")

    # Final verification
    missing_after = _get_missing_items()
    if missing_after:
        _print(f"[OpenAddrBR] WARNING: Still missing after download: {', '.join(missing_after)}")
    else:
        _print(f"[OpenAddrBR] Setup complete! All data and model are ready.")

    return data_path


def check_data_exists() -> bool:
    """Check if all required files exist (data + model)."""
    return not _get_missing_items()