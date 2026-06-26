"""
Extract per-membrane ground-truth Latin text from Maitland 1884 HTML.

Source: Internet Archive DjVu OCR of crowncountyplea00glouuoft, saved as HTML.
Each [Memb. N.] / [Memb. N dors.] section is extracted, cleaned, and written
to data/ground_truth/{membrane_ref}.txt for use in CER/WER scoring.

Membrane reference mapping (established from confirmed anchor):
  Maitland [Memb. 10.]      = AALT IMG_3878 = our membrane ref m24
  Formula: Maitland N face  → m{N+14}
           Maitland N dorse → m{N+14}d
  OFFSET = 14

This offset is confirmed: the user verified IMG_3878 = [Memb. 10.].
Adjacent membranes follow arithmetically from the same anchor; each
should be spot-checked against the image before its score is reported.

OCR cleaning applied:
  - HTML entity decoding (&lt; → <, etc.)
  - Collapse runs of 2+ spaces to one (DjVu OCR inserts extra spaces)
  - Strip repeated section headers (PLACITA CORONE, AMERCIAMENTA, etc.)
  - Strip footnote lines (start with ^ * ¹ ² ³ or are bare numbers)
  - Preserve paragraph breaks (blank lines between pleas)
"""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HTML_GLOB = list(REPO_ROOT.glob("Full text of *.html"))
GROUND_TRUTH_DIR = REPO_ROOT / "data" / "ground_truth"

# Maitland membrane N → our ref offset: m(N+14) or m(N+14)d
MAITLAND_OFFSET = 14

# Header lines to strip from every section (OCR page headers)
_STRIP_HEADERS = re.compile(
    r"^\s*(?:PLACITA\s+(?:CO|C O)\s*(?:RON[AE]|R O N E)\b.*"
    r"|AMERCIAMENT[A-Z]*\b.*"
    r"|DE\s+COMITATU\s+GLOUC.*"
    r"|REGIS\s+HENRICI.*"
    r"|HUNDREDA\b.*"
    r"|APPENDIX.*"
    r")\s*$",
    re.IGNORECASE,
)

# Footnote lines: start with ^ * superscript digits, or are standalone page/footnote numbers
_STRIP_FOOTNOTE = re.compile(
    r"^\s*[\^*¹²³⁴⁵⁶⁷⁸⁹⁰†‡§¶]+.*$"
    r"|^\s*\d+\s*$"                    # bare page numbers
    r"|^\s*'[^']{0,60}'\s*$"           # short footnote references like ' See note.'
)


def _extract_pre_content(html_path: Path) -> str:
    """Pull the raw text out of the single <pre> block."""
    raw = html_path.read_text(encoding="utf-8", errors="replace")
    m = re.search(r"<pre>(.*?)</pre>", raw, re.DOTALL)
    if not m:
        raise ValueError(f"No <pre> block found in {html_path}")
    return html.unescape(m.group(1))


def _split_by_membrane(text: str) -> list[tuple[str, str]]:
    """
    Split the pre content into (membrane_label, text) pairs.

    Labels look like 'Memb. 10', 'Memb. 10 dors.', etc.
    Everything before the first [Memb. ...] marker is discarded
    (title pages, introduction, indices).
    """
    # Match [Memb.  10.] or [Memb.  10  dors.] or [Memb.  12  dors,] (OCR comma variant)
    marker_re = re.compile(
        r"\[Memb\.\s+(\d+)[\.\s]*(dors[.,]?)?\s*\]",
        re.IGNORECASE,
    )

    sections: list[tuple[str, str]] = []
    positions = [(m.start(), m.group(1), m.group(2)) for m in marker_re.finditer(text)]

    for i, (start, num, dors) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        # Skip the marker line itself
        section_text = text[start:end]
        section_text = section_text[section_text.index("]") + 1:]
        label = f"Memb. {num} dors." if dors else f"Memb. {num}"
        sections.append((label, section_text))

    return sections


def _clean(text: str) -> str:
    """Clean OCR artifacts from a membrane section."""
    lines = text.splitlines()
    cleaned = []
    for line in lines:
        # Collapse multiple spaces to one
        line = re.sub(r" {2,}", " ", line)
        # Strip leading/trailing whitespace
        line = line.strip()
        # Drop section header repeats and footnote lines
        if _STRIP_HEADERS.match(line):
            continue
        if _STRIP_FOOTNOTE.match(line):
            continue
        cleaned.append(line)

    # Collapse runs of 3+ blank lines to a single blank line
    result = re.sub(r"\n{3,}", "\n\n", "\n".join(cleaned))
    return result.strip()


def maitland_label_to_ref(num: int, dorse: bool) -> str:
    """Convert a Maitland membrane number to our AALT membrane ref."""
    our_num = num + MAITLAND_OFFSET
    return f"m{our_num}d" if dorse else f"m{our_num}"


def extract_all(html_path: Path, output_dir: Path) -> list[dict]:
    """
    Extract all membrane sections from html_path and write to output_dir.

    Returns a list of records suitable for updating the concordance.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    pre = _extract_pre_content(html_path)
    sections = _split_by_membrane(pre)

    records = []
    for label, raw_text in sections:
        # Parse the label
        m = re.match(r"Memb\. (\d+)(?: (dors\.))?", label)
        if not m:
            continue
        num = int(m.group(1))
        dorse = bool(m.group(2))
        ref = maitland_label_to_ref(num, dorse)

        cleaned = _clean(raw_text)
        out_path = output_dir / f"{ref}.txt"
        out_path.write_text(cleaned, encoding="utf-8")

        records.append({
            "membrane_ref": ref,
            "maitland_label": label,
            "maitland_membrane_num": num,
            "is_dorse": dorse,
            "output_path": str(out_path),
            "char_count": len(cleaned),
        })
        print(f"  {ref:8s}  ←  {label:20s}  {len(cleaned):5d} chars  →  {out_path.name}")

    return records


def main() -> int:
    if not HTML_GLOB:
        print(
            "ERROR: Maitland HTML not found in repo root.\n"
            "Expected: 'Full text of _Pleas of the Crown..._.html'",
            file=sys.stderr,
        )
        return 1

    html_path = HTML_GLOB[0]
    print(f"Source: {html_path.name}")
    print(f"Output: {GROUND_TRUTH_DIR}\n")

    records = extract_all(html_path, GROUND_TRUTH_DIR)
    print(f"\nExtracted {len(records)} membrane sections.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
