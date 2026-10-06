"""
CLI entry point for Stage 6 (collate).

Usage:
    python -m src.collate.run
    python -m src.collate.run --metrics output/metrics
"""

import argparse
import sys
from pathlib import Path

from .collator import annotate_canonical_hundred, build_database, build_hundred_summary

REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = REPO_ROOT / "output" / "metrics"
DB_PATH = REPO_ROOT / "output" / "eyre1221.db"
HUNDRED_LOOKUP_PATH = REPO_ROOT / "data" / "hundred_lookup.csv"
HUNDRED_COORDS_PATH = REPO_ROOT / "data" / "hundred_coords.csv"
HUNDRED_SUMMARY_PATH = REPO_ROOT / "output" / "hundreds.csv"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collate case CSVs into SQLite database")
    parser.add_argument("--metrics", type=Path, default=METRICS_DIR,
                        help="Directory containing *_cases.csv files")
    parser.add_argument("--db", type=Path, default=DB_PATH,
                        help="Output database path")
    parser.add_argument("--exclude", nargs="+", default=[], metavar="REF",
                        help="Membrane refs to exclude (e.g. m34 m35 m38d)")
    parser.add_argument("--hundred-lookup", type=Path, default=HUNDRED_LOOKUP_PATH,
                        help="Raw heading -> canonical hundred lookup CSV")
    parser.add_argument("--hundred-coords", type=Path, default=HUNDRED_COORDS_PATH,
                        help="Canonical hundred -> lat/lon CSV")
    parser.add_argument("--hundred-summary", type=Path, default=HUNDRED_SUMMARY_PATH,
                        help="Output path for the per-hundred plea count/coordinate summary")
    args = parser.parse_args()

    csv_paths = sorted(
        p for p in args.metrics.glob("*_cases.csv")
        if p.stem.replace("_cases", "") not in args.exclude
    )
    if not csv_paths:
        print(f"ERROR: no *_cases.csv files found in {args.metrics}", file=sys.stderr)
        return 1

    print(f"Found {len(csv_paths)} CSV(s): {[p.name for p in csv_paths]}")
    count = build_database(csv_paths, args.db)
    print(f"Database written: {args.db}  ({count} pleas)")

    annotate_canonical_hundred(args.db, args.hundred_lookup)

    summary = build_hundred_summary(
        args.db, args.hundred_lookup, args.hundred_coords, args.hundred_summary
    )
    unresolved = [r for r in summary if r["status"] == "unresolved"]
    print(f"Hundred summary written: {args.hundred_summary}  "
          f"({len(summary)} hundreds, {len(unresolved)} unresolved)")
    for r in unresolved:
        print(f"  unresolved: {r['canonical_hundred']} ({r['plea_count']} pleas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
