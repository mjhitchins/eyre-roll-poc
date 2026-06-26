"""
CLI entry point for Stage 7 (publish).

Usage:
    python -m src.publish.run
    python -m src.publish.run --db output/eyre1221.db

After running, preview locally with:
    python -m http.server 8000 --directory docs/
then open http://localhost:8000
"""

import argparse
import sys
from pathlib import Path

from .publisher import publish, DB_SRC, SITE_DIR


def main() -> int:
    parser = argparse.ArgumentParser(description="Copy database to docs/ for GitHub Pages")
    parser.add_argument("--db", type=Path, default=DB_SRC,
                        help="Source database (default: output/eyre1221.db)")
    args = parser.parse_args()

    if not args.db.exists():
        print(f"ERROR: database not found: {args.db}", file=sys.stderr)
        print("Run Stage 6 first: python -m src.collate.run", file=sys.stderr)
        return 1

    dest = publish(db_path=args.db)
    print(f"Published: {dest}")
    print(f"Preview:   python -m http.server 8000 --directory docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
