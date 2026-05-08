"""Hugging Face data download manager."""

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
        files = list_repo_files(repo_id=REPO_ID, repo_type="dataset")
        result = {}
        for f in files:
            if f.endswith(".tar.zst"):
                result[f] = f  # key == value for now, maps remote name to local target
        return result
    except Exception:
        return {}


def _verify_zst(path: Path) -> bool:
    """Check if file is a valid zstd archive (magic bytes)."""
    ZSTD_MAGIC = b'\x28\xb5\x2f\xfd'
    try:
        with open(path, 'rb') as f:
            return f.read(4) == ZSTD_MAGIC
    except Exception:
        return False


def _download_compressed_file(filename: str, dest_dir: Path, force: bool = False) -> Path:
    """Download a single .tar.zst file from HF and return local path."""
    from huggingface_hub import hf_hub_download
    import tempfile
    import shutil

    local_path = dest_dir / filename
    if local_path.exists() and not force:
        return local_path

    # Remove existing locked file before download if possible
    if local_path.exists():
        try:
            local_path.unlink()
        except PermissionError:
            pass  # Will download to temp and we handle below

    # Download to temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        downloaded = hf_hub_download(
            repo_id=REPO_ID,
            filename=filename,
            repo_type="dataset",
            local_dir=tmpdir,
        )
        downloaded_path = Path(downloaded)

        # Try to replace destination file
        try:
            if local_path.exists():
                local_path.unlink()
            shutil.copy2(downloaded, str(local_path))
        except (PermissionError, FileExistsError):
            # Destination is locked - keep downloaded file in temp dir
            # Return a path that won't conflict (use original path for caller)
            # But since caller will try to extract from returned path,
            # we need to actually make the file accessible
            # Copy to dest with different name
            temp_copy = dest_dir / f".tmp_{filename}"
            shutil.copy2(downloaded, str(temp_copy))
            return temp_copy

    return local_path


def _extract_tar_zst(tar_path: Path, dest_dir: Path, remove_after: bool = True) -> None:
    """Extract a .tar.zst file using zstandard streaming + tarfile."""
    _print(f"[OpenAddrBR] Extracting {tar_path.name}...")

    if not _verify_zst(tar_path):
        raise RuntimeError(f"{tar_path.name} is not a valid zstd archive. Download may be corrupted.")

    extracted_ok = False
    try:
        with open(tar_path, "rb") as fin:
            dctx = zstd.ZstdDecompressor()
            with dctx.stream_reader(fin) as zst_reader:
                with tarfile.open(fileobj=zst_reader, mode="r|") as tar:
                    for member in tar:
                        tar.extract(member, path=dest_dir)

        extracted_ok = True
        _print(f"[OpenAddrBR] Extracted: {tar_path.name}")
    except Exception as e:
        _print(f"[OpenAddrBR] Extraction failed: {e}")
        raise

    if remove_after and extracted_ok:
        tar_path.unlink()
        _print(f"[OpenAddrBR] Removed: {tar_path.name}")


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
    """Download and extract data from Hugging Face Hub (.tar.zst archives)."""
    if not HF_AVAILABLE:
        raise ImportError(
            "huggingface_hub not installed. Install with: pip install huggingface_hub"
        )

    data_path = get_data_path()

    _print(f"[OpenAddrBR] Data path: {data_path}")

    # Check what's missing locally
    missing_local = _get_missing_items()

    if not missing_local and not force:
        _print(f"[OpenAddrBR] All data already exists! Nothing to download.")
        return data_path

    if missing_local:
        _print(f"[OpenAddrBR] Missing: {', '.join(missing_local)}")

    ensure_data_path()

    # Get available compressed files on remote
    remote_files = _get_remote_compressed_files()
    _print(f"[OpenAddrBR] Remote .tar.zst files: {list(remote_files.keys())}")

    # Download and extract .tar.zst for each required item
    for local_name, remote_name in [("sgeobr.db", COMPRESSED_SGEEBR_DB), ("usearch_v2/", COMPRESSED_USEARCH)]:
        if local_name in missing_local and remote_name in remote_files:
            _print(f"[OpenAddrBR] Downloading {remote_name}...")
            tar_path = _download_compressed_file(remote_name, data_path, force=force)
            _print(f"[OpenAddrBR] Extracting {tar_path.name}...")
            _extract_tar_zst(Path(tar_path), data_path)

    _print(f"[OpenAddrBR] HF data extracted to {data_path}")

    # Download sentence-transformers model (unchanged)
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