"""
CLI entry point for Stage 3 (transcribe).

Usage:
    python -m src.transcribe.run --membrane m1 --model models/catmus-medieval.mlmodel
    python -m src.transcribe.run --membrane m1 m2 m1d --model models/catmus-medieval.mlmodel
    python -m src.transcribe.run --membrane m1 --model models/catmus-medieval.mlmodel --force

Reads clean images from data/images_clean/{membrane_ref}.jpg
Writes transcripts to output/transcripts/{membrane_ref}.txt

See MODELS.md for how to download a suitable Kraken model.
"""

import argparse
import logging
import sys
from pathlib import Path

from .transcriber import transcribe_membrane

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

REPO_ROOT = Path(__file__).resolve().parents[2]
IMAGES_CLEAN = REPO_ROOT / "data" / "images_clean"
TRANSCRIPTS_OUT = REPO_ROOT / "output" / "transcripts"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcribe preprocessed AALT membrane images to Latin text via Kraken HTR"
    )
    parser.add_argument(
        "--membrane", nargs="+", required=True, metavar="REF",
        help="Membrane refs to transcribe, e.g. m1 m2 m1d",
    )
    parser.add_argument(
        "--model", required=True, metavar="PATH",
        help="Path to a Kraken .mlmodel file (see MODELS.md)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-transcribe even if transcript already exists",
    )
    args = parser.parse_args()

    model_path = Path(args.model)
    records = []

    for ref in args.membrane:
        clean_path = IMAGES_CLEAN / f"{ref}.jpg"
        try:
            record = transcribe_membrane(
                membrane_ref=ref,
                clean_image_path=clean_path,
                output_dir=TRANSCRIPTS_OUT,
                model_path=model_path,
                force=args.force,
            )
            records.append(record)
            if record.get("skipped"):
                print(f"SKIPPED {ref}: {record['transcript_path']}")
            else:
                print(f"OK      {ref}: {record['transcript_path']}")
        except FileNotFoundError as exc:
            print(f"ERROR   {ref}: {exc}", file=sys.stderr)
            return 1

    processed = sum(1 for r in records if not r.get("skipped"))
    print(f"\nTranscribed {processed} membrane(s) → {TRANSCRIPTS_OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
