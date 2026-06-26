"""
CLI entry point for Stage 4 (score).

Usage:
    python -m src.score.run data/ground_truth/m24.txt output/transcripts/m24.txt
    python -m src.score.run data/ground_truth/m24.txt output/transcripts/m24.txt --membrane m24
"""

import argparse
import sys
from pathlib import Path

from .scorer import score


def main() -> int:
    parser = argparse.ArgumentParser(description="Score a Kraken transcript against Maitland ground truth")
    parser.add_argument("reference", type=Path, help="Ground truth file (Maitland text)")
    parser.add_argument("hypothesis", type=Path, help="Transcript file (Kraken output)")
    parser.add_argument("--membrane", default=None, help="Membrane ref label for the report")
    args = parser.parse_args()

    if not args.reference.exists():
        print(f"ERROR: reference file not found: {args.reference}", file=sys.stderr)
        return 1
    if not args.hypothesis.exists():
        print(f"ERROR: transcript file not found: {args.hypothesis}", file=sys.stderr)
        return 1

    ref = args.reference.read_text(encoding="utf-8")
    hyp = args.hypothesis.read_text(encoding="utf-8")

    membrane = args.membrane or args.hypothesis.stem
    result = score(hypothesis=hyp, reference=ref, membrane_ref=membrane)

    print(f"Membrane : {membrane}")
    print(f"CER      : {result.cer:.3f}  ({result.cer*100:.1f}%)")
    print(f"WER      : {result.wer:.3f}  ({result.wer*100:.1f}%)")
    print(f"Ref      : {result.ref_words} words / {result.ref_chars} chars")
    print(f"Hyp      : {result.hyp_words} words / {result.hyp_chars} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
