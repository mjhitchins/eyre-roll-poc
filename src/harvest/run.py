"""
CLI entry point for Stage 1 (harvest).

Usage:
    python -m src.harvest.run --membrane m1
    python -m src.harvest.run --membrane m1 m2 m3
    python -m src.harvest.run --all-fronts
"""

import argparse
import logging
import sys
from pathlib import Path

import requests

from .harvester import (
    _FRONTS_FIRST, _FRONTS_LAST, _DORSES_FIRST, _DORSES_LAST,
    download_membrane_image, write_manifest,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES_RAW = REPO_ROOT / "data" / "images_raw"
MANIFEST_DIR = IMAGES_RAW


def all_fronts() -> list[str]:
    return [f"m{n}" for n in range(1, _FRONTS_LAST - _FRONTS_FIRST + 2)]


def all_dorses() -> list[str]:
    return [f"m{n}d" for n in range(1, _DORSES_LAST - _DORSES_FIRST + 2)]


def main() -> int:
    parser = argparse.ArgumentParser(description="Harvest AALT images for JUST 1/271")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--membrane", nargs="+", metavar="REF",
                       help="Membrane refs to download, e.g. m1 m2 m1d")
    group.add_argument("--all-fronts", action="store_true",
                       help="Download all membrane faces (m1–m55)")
    group.add_argument("--all-dorses", action="store_true",
                       help="Download all membrane dorses (m1d–m46d)")
    args = parser.parse_args()

    if args.all_fronts:
        refs = all_fronts()
    elif args.all_dorses:
        refs = all_dorses()
    else:
        refs = args.membrane

    downloaded = []
    session = requests.Session()
    try:
        for ref in refs:
            path = download_membrane_image(ref, IMAGES_RAW, session=session)
            downloaded.append(path)
    finally:
        session.close()

    write_manifest(refs, downloaded, MANIFEST_DIR)
    print(f"Downloaded {len(downloaded)} image(s) to {IMAGES_RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
