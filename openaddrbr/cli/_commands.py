"""CLI commands for openaddrbr."""

import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

import torch

from openaddrbr.core._encoder import VALID_BACKENDS, Encoder
from openaddrbr.data import check_data_exists, download_data, get_data_path


def _get_sample_addresses() -> list[str]:
    """Load sample addresses for benchmarking."""
    # Try package data first
    pkg_data = Path(__file__).parent.parent / "data" / "sample_addresses.json"
    if pkg_data.exists():
        with open(pkg_data, encoding="utf-8") as f:
            data = json.load(f)
            return [f"{r['street']} - {r['neighborhood']}" for r in data]

    # Fallback to benchmark data
    benchmark_data = Path(__file__).parent.parent.parent / "benchmarks" / "google_ref_lat_long.json"
    if benchmark_data.exists():
        with open(benchmark_data, encoding="utf-8") as f:
            records = json.load(f)
            return [
                r.get("place", {}).get("street", "")
                for r in records[:500]
                if r.get("place", {}).get("street")
            ]

    return []


def _run_benchmark_for_backend(
    backend: str, addresses: list[str], batch_sizes: list[int]
) -> list[dict]:
    """Run benchmark for a specific backend."""
    results = []
    # Ensure at least 200 addresses for reliable benchmark
    addresses = (addresses * max(1, (200 // len(addresses)) + 1))[:200]
    try:
        encoder = Encoder(backend=backend)
        for batch_size in batch_sizes:
            start = time.perf_counter()
            encoder.encode_batch(addresses, batch_size=batch_size)
            elapsed = time.perf_counter() - start
            streets_per_sec = len(addresses) / elapsed
            results.append(
                {
                    "backend": backend,
                    "batch": batch_size,
                    "streets_per_sec": streets_per_sec,
                }
            )
    except Exception as e:
        print(f"  ! {backend}: failed ({e})")
    return results


def _update_env_file(recommended: str, env_path: Path) -> None:
    """Update .env with OpenAddrBR settings, preserving existing content."""
    header_comments = [
        "# OpenAddrBR Configuration",
        "#",
        "# Backend options: pytorch, pytorch-compiled, onnx, onnx-int8, cuda",
        "#   - pytorch: plain PyTorch (no compile)",
        "#   - pytorch-compiled: PyTorch + torch.compile (default, best accuracy)",
        "#   - onnx: ONNX float32 (no quantization)",
        "#   - onnx-int8: ONNX int8 (fast but quantized, may reduce accuracy)",
        "#   - cuda: PyTorch GPU with float16",
        "#",
    ]

    new_vars = {
        "OPENADDRBR_BACKEND": recommended,
        "OPENADDRBR_BATCH_SIZE": "16",
    }

    if env_path.exists():
        # Read existing file
        with open(env_path, encoding="utf-8") as f:
            lines = f.read().splitlines()

        # Separate existing OpenAddrBR lines from others
        other_lines = []
        existing_keys = set()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("OPENADDRBR_"):
                key = stripped.split("=")[0]
                existing_keys.add(key)
                if key in new_vars:
                    other_lines.append(f"{key}={new_vars[key]}")
            else:
                other_lines.append(line)

        # Add new OpenAddrBR vars that didn't exist
        for key, value in new_vars.items():
            if key not in existing_keys:
                other_lines.append(f"{key}={value}")

        # Write back with header at top
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header_comments) + "\n")
            f.write("\n".join(other_lines) + "\n")
    else:
        # New file - write with header
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header_comments) + "\n")
            for key, value in new_vars.items():
                f.write(f"{key}={value}\n")


def _main(args=None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="openaddrbr",
        description="Brazilian address geocoder using vector search",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # download command
    download_parser = subparsers.add_parser("download", help="Download data from Hugging Face")
    download_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if data exists"
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Show data location and status")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Setup and tune performance")

    args = parser.parse_args(args)

    if args.command == "download":
        try:
            download_data(force=args.force)
        except Exception as e:
            print(f"Error downloading data: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "info":
        data_path = get_data_path()
        exists = check_data_exists()
        print(f"Data path: {data_path}")
        print(f"Data present: {'Yes' if exists else 'No'}")

    elif args.command == "setup":
        print()
        print("=" * 60)
        print("  [Setup] OpenAddrBR - Performance Tuning")
        print("=" * 60)
        print()

        # Detect hardware
        cuda_available = torch.cuda.is_available()
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            print(f"  Detected: {gpu_name} (CUDA available)")
        else:
            print(f"  Detected: {platform.system()} {platform.machine()}, CPU only")
        print()

        # Load sample addresses
        addresses = _get_sample_addresses()
        if not addresses:
            print("  Error: No sample addresses found for benchmark.")
            print("  Please ensure sample_addresses.json exists or benchmark data is available.")
            sys.exit(1)

        print(f"  Running benchmark (~{max(200, len(addresses))} samples)...")
        print()

        # Test backends
        batch_sizes = [8, 16, 32]
        all_results = []

        # CPU backends
        cpu_backends = [b for b in VALID_BACKENDS if b not in ("cuda",)]
        print("  === CPU Results ===")
        for backend in cpu_backends:
            results = _run_benchmark_for_backend(backend, addresses, batch_sizes)
            if not results:
                continue
            best_for_backend = max(results, key=lambda x: x["streets_per_sec"])
            for r in results:
                label = f"  {r['backend']:<20} @ batch={r['batch']:>2}: {r['streets_per_sec']:>6.0f} streets/sec"
                if r["backend"] == "onnx-int8":
                    label += "  [QUANTIZED]"
                if (
                    r["backend"] == best_for_backend["backend"]
                    and r["batch"] == best_for_backend["batch"]
                ):
                    label += "  [BEST]"
                print(label)
                all_results.append(r)
        print()

        # GPU backends
        if cuda_available:
            print("  === GPU Results ===")
            results = _run_benchmark_for_backend("cuda", addresses, batch_sizes)
            if not results:
                print("  ! cuda: failed (no results)")
            else:
                best_for_backend = max(results, key=lambda x: x["streets_per_sec"])
                for r in results:
                    label = f"  cuda              @ batch={r['batch']:>2}: {r['streets_per_sec']:>6.0f} streets/sec"
                    if r["batch"] == best_for_backend["batch"]:
                        label += "  [BEST]"
                    print(label)
                    all_results.append(r)
            print()

        # Find best result (prioritize non-quantized)
        # Filter out quantized backends from recommendation
        non_quantized = [r for r in all_results if r["backend"] != "onnx-int8"]
        if non_quantized:
            best = max(non_quantized, key=lambda x: x["streets_per_sec"])
        else:
            best = max(all_results, key=lambda x: x["streets_per_sec"])
        best_backend = best["backend"]
        best_batch = best["batch"]

        # Determine recommended backend (never recommend quantized)
        if cuda_available and best["backend"] == "cuda":
            recommended = "cuda"
        elif best_backend in ("onnx-int8", "onnx"):
            # Never recommend quantized or ONNX float32 - use pytorch-compiled
            pytorch_results = [r for r in all_results if r["backend"] == "pytorch-compiled"]
            if pytorch_results:
                recommended = "pytorch-compiled"
            else:
                recommended = "pytorch"
        else:
            recommended = best_backend

        # Show warning if ONNX int8 was fastest
        onnx_int8_results = [r for r in all_results if r["backend"] == "onnx-int8"]
        if onnx_int8_results:
            best_onnx_int8 = max(onnx_int8_results, key=lambda x: x["streets_per_sec"])
            if best_onnx_int8["streets_per_sec"] > best["streets_per_sec"]:
                print(
                    f"  Note: ONNX int8 was fastest ({best_onnx_int8['streets_per_sec']:.0f} streets/sec)"
                )
                print(f"         but is quantized - using pytorch-compiled for accuracy")
                print()

        print(f"  [OK] Detected best backend: OPENADDRBR_BACKEND={recommended}")

        # Update .env file (preserves existing content)
        env_path = Path.cwd() / ".env"
        _update_env_file(recommended, env_path)
        print(f"  [OK] Written to .env")
        print()

        if recommended == "onnx-int8":
            print("  [!] Note: ONNX int8 uses quantization which may reduce")
            print("         geocoding accuracy. Using pytorch-compiled for best quality.")
            print()

        if cuda_available and best["backend"] == "cuda":
            speedup = best["streets_per_sec"] / max(
                r["streets_per_sec"] for r in all_results if r["backend"] == "pytorch-compiled"
            )
            print(f"  [!] Your GPU is {speedup:.1f}x faster than CPU for encoding.")
            print()

        print("  Ready to use!")
        print()

    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
