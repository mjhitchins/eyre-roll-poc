"""
CLI entry point for Stage 2 (preprocess).

Usage:
    python -m src.preprocess.run --membrane m1
    python -m src.preprocess.run --membrane m1 m2 m1d
    python -m src.preprocess.run --membrane m1 --force
"""

import argparse
import logging
import sys
from pathlib import Path

from .preprocessor import preprocess_image, write_manifest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES_RAW = REPO_ROOT / "data" / "images_raw"
IMAGES_CLEAN = REPO_ROOT / "data" / "images_clean"


def main() -> int:
    parser = argparse.ArgumentParser(description="Preprocess AALT membrane images")
    parser.add_argument("--membrane", nargs="+", required=True, metavar="REF",
                        help="Membrane refs to preprocess, e.g. m1 m2 m1d")
    parser.add_argument("--force", action="store_true",
                        help="Reprocess even if output already exists")
    args = parser.parse_args()

    records = []
    for ref in args.membrane:
        input_path = IMAGES_RAW / f"{ref}.jpg"
        output_path = IMAGES_CLEAN / f"{ref}.jpg"

        if not input_path.exists():
            print(f"ERROR: raw image not found: {input_path}", file=sys.stderr)
            return 1

        record = preprocess_image(input_path, output_path, force=args.force)
        record["membrane_ref"] = ref
        records.append(record)

    write_manifest(records, IMAGES_CLEAN)
    processed = sum(1 for r in records if not r.get("skipped"))
    print(f"Preprocessed {processed} image(s) → {IMAGES_CLEAN}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
