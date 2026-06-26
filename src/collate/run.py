"""
CLI entry point for Stage 6 (collate).

Usage:
    python -m src.collate.run
    python -m src.collate.run --metrics output/metrics
"""

import argparse
import sys
from pathlib import Path

from .collator import build_database

REPO_ROOT = Path(__file__).resolve().parents[2]
METRICS_DIR = REPO_ROOT / "output" / "metrics"
DB_PATH = REPO_ROOT / "output" / "eyre1221.db"


def main() -> int:
    parser = argparse.ArgumentParser(description="Collate case CSVs into SQLite database")
    parser.add_argument("--metrics", type=Path, default=METRICS_DIR,
                        help="Directory containing *_cases.csv files")
    parser.add_argument("--db", type=Path, default=DB_PATH,
                        help="Output database path")
    args = parser.parse_args()

    csv_paths = sorted(args.metrics.glob("*_cases.csv"))
    if not csv_paths:
        print(f"ERROR: no *_cases.csv files found in {args.metrics}", file=sys.stderr)
        return 1

    print(f"Found {len(csv_paths)} CSV(s): {[p.name for p in csv_paths]}")
    count = build_database(csv_paths, args.db)
    print(f"Database written: {args.db}  ({count} pleas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
