"""Hugging Face data download manager."""

import sys
import tarfile
import zstandard as zstd
from pathlib import Path

try:
    import huggingface_hub
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

from openaddrbr.data._config import get_data_path, ensure_data_path, get_sgeodb_path, get_usearch_dir, get_model_path

REPO_ID = "jpsamarino/OpenAddrBR"
MODEL_NAME = "sentence-transformers/paraphrase-xlm-r-multilingual-v1"

COMPRESSED_SGEEBR_DB = "sgeobr.db.tar.zst"
COMPRESSED_USEARCH = "usearch_v2.tar.zst"


def _print(msg: str) -> None:
    """Print message to stderr to avoid polluting stdout."""
    print(msg, file=sys.stderr)


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


def _download(filename: str, dest_dir: Path) -> Path:
    """Download a .tar.zst file from HF into dest_dir."""
    from huggingface_hub import hf_hub_download
    local_path = dest_dir / filename
    if local_path.exists():
        try:
            local_path.unlink()
        except PermissionError:
            pass
    hf_hub_download(
        repo_id=REPO_ID,
        filename=filename,
        repo_type="dataset",
        local_dir=str(dest_dir),
    )
    return local_path


def _extract(tar_path: Path, dest_dir: Path) -> None:
    """Extract a .tar.zst using streaming zstd + tarfile pipe."""
    _print(f"[OpenAddrBR] Extracting {tar_path.name}...")
    with open(tar_path, "rb") as fin:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fin) as zst_reader:
            with tarfile.open(fileobj=zst_reader, mode="r|") as tar:
                for member in tar:
                    tar.extract(member, path=dest_dir)
    tar_path.unlink()
    _print(f"[OpenAddrBR] Removed: {tar_path.name}")


def download_data(force: bool = False) -> Path:
    """Download and extract data from Hugging Face Hub (.tar.zst archives)."""
    if not HF_AVAILABLE:
        raise ImportError(
            "huggingface_hub not installed. Install with: pip install huggingface_hub"
        )

    data_path = get_data_path()
    _print(f"[OpenAddrBR] Data path: {data_path}")

    missing_local = _get_missing_items()
    if not missing_local and not force:
        _print("[OpenAddrBR] All data already exists! Nothing to download.")
        return data_path

    if missing_local:
        _print(f"[OpenAddrBR] Missing: {', '.join(missing_local)}")

    ensure_data_path()

    # Download and extract each .tar.zst
    for local_name, remote_name in [
        ("sgeobr.db", COMPRESSED_SGEEBR_DB),
        ("usearch_v2/", COMPRESSED_USEARCH),
    ]:
        if local_name in missing_local:
            _print(f"[OpenAddrBR] Downloading {remote_name}...")
            tar_path = _download(remote_name, data_path)
            _print(f"[OpenAddrBR] Extracting {tar_path.name}...")
            _extract(tar_path, data_path)

    _print(f"[OpenAddrBR] HF data extracted to {data_path}")

    # Download sentence-transformers model
    model_path = get_model_path()
    if not model_path.exists() or force:
        _print("[OpenAddrBR] Downloading sentence-transformers model...")
        from sentence_transformers import SentenceTransformer
        model_path.parent.mkdir(parents=True, exist_ok=True)
        _print(f"[OpenAddrBR] Downloading model to {model_path}...")
        tmp_model = SentenceTransformer(MODEL_NAME)
        tmp_model.save(str(model_path))
        _print(f"[OpenAddrBR] Model saved to {model_path}")
    else:
        _print(f"[OpenAddrBR] Model already exists at {model_path}")

    missing_after = _get_missing_items()
    if missing_after:
        _print(f"[OpenAddrBR] WARNING: Still missing: {', '.join(missing_after)}")
    else:
        _print("[OpenAddrBR] Setup complete! All data and model are ready.")

    return data_path


def check_data_exists() -> bool:
    """Check if all required files exist."""
    return not _get_missing_items()