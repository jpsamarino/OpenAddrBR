"""CLI commands for openaddrbr."""

import argparse
import sys
from pathlib import Path

from openaddrbr.data import check_data_exists, download_data, get_data_path


def _main(args=None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="openaddrbr",
        description="Brazilian address geocoder using vector search",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # download command
    download_parser = subparsers.add_parser(
        "download", help="Download data from Hugging Face"
    )
    download_parser.add_argument(
        "--force", action="store_true", help="Force re-download even if data exists"
    )

    # info command
    info_parser = subparsers.add_parser("info", help="Show data location and status")

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

    else:
        parser.print_help()


if __name__ == "__main__":
    _main()