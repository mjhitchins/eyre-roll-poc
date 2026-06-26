"""
CLI entry point for Stage 5 (structure).

Usage:
    python -m src.structure.run --membrane m24
    python -m src.structure.run --membrane m24 m25 m26
"""

import argparse
import sys
from pathlib import Path

from .structurer import parse_pleas, write_csv

REPO_ROOT = Path(__file__).resolve().parents[2]
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"
METRICS_DIR = REPO_ROOT / "output" / "metrics"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract structured case fields from Maitland ground-truth text"
    )
    parser.add_argument("--membrane", nargs="+", required=True, metavar="REF")
    args = parser.parse_args()

    for ref in args.membrane:
        gt_path = GROUND_TRUTH_DIR / f"{ref}.txt"
        if not gt_path.exists():
            print(f"ERROR: ground truth not found: {gt_path}", file=sys.stderr)
            return 1

        text = gt_path.read_text(encoding="utf-8")
        records = parse_pleas(text, membrane_ref=ref)

        out_path = METRICS_DIR / f"{ref}_cases.csv"
        write_csv(records, out_path)

        print(f"{ref}: {len(records)} pleas → {out_path}")
        for r in records:
            print(f"  {r.plea_num:>3}.  {r.offence_type:<28}  {r.verdict:<25}  {r.amercement_raw}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
