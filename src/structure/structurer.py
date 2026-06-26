"""
Stage 5: Extract structured fields from Maitland ground-truth Latin text.

Parses numbered plea entries and extracts:
  - hundred         : hundred (or vill) the plea falls under
  - party_1         : first named party (perpetrator, appellant, or victim)
  - party_2         : second named party (victim or appellee, where extractable)
  - offence_latin   : raw Latin offence phrase detected
  - offence_type    : normalised English category
  - verdict         : primary Latin verdict phrase
  - amercement_raw  : amount as it appears in the text (OCR-dirty)

Detection is keyword-based on the formulaic Latin of 13th-century crown pleas.

Hundred header OCR variants seen across membranes:
  Htmdredum / Hnndrcdum / Hundrediim / Hundredum — all mean "Hundredum de X"
  Adhuc de Hundredo de X — continuation of the same hundred across a membrane
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# Location (hundred / vill) detection
# ---------------------------------------------------------------------------

# Matches OCR-corrupted "Hundredum de X" and "Adhuc de Hundredo de X"
_HUNDRED_RE = re.compile(
    r"""
    (?:
        H\w{0,6}d(?:um|iim|urn)\s+de   # Hundredum / Htmdredum / Hundrediim etc.
      | Adhuc\s+de\s+Hundredo\s+de      # continuation: Adhuc de Hundredo de X
    )
    \s+([\w\s]+?)                        # the hundred name
    [\.\n^']                             # terminated by period, newline or OCR junk
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Standalone "Villata de X." on its own line — marks a vill sub-section
_VILL_RE = re.compile(
    r"^Villata\s+de\s+([\w\s]+?)\s*\.\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def _build_location_map(text: str) -> list[tuple[int, str]]:
    """
    Return a list of (char_position, location_name) in document order.
    Each plea is assigned the most recent location before its start.
    """
    locations: list[tuple[int, str]] = []
    for m in _HUNDRED_RE.finditer(text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        locations.append((m.start(), name))
    for m in _VILL_RE.finditer(text):
        name = re.sub(r"\s+", " ", m.group(1)).strip()
        locations.append((m.start(), name))
    return sorted(locations, key=lambda x: x[0])


def _location_at(pos: int, location_map: list[tuple[int, str]]) -> str:
    """Return the most recent location name before pos."""
    result = ""
    for loc_pos, name in location_map:
        if loc_pos <= pos:
            result = name
        else:
            break
    return result


# ---------------------------------------------------------------------------
# Party name extraction
# ---------------------------------------------------------------------------

# Main Latin verbs that signal the end of the subject name phrase
_VERB_RE = re.compile(
    r"\b(occidit|occiderunt|appellavit|appellaverunt|suspendit|rettatus|rettati|"
    r"vendiderunt|inventus|inventa|assisa|dat\b|non\s+est\s+servata|fuit\s+in\b|"
    r"fugerunt|fugit\b|venit\b|venerunt)\b",
    re.IGNORECASE,
)

# Accusative/object name after "occidit" or "occiderunt"
_VICTIM_RE = re.compile(
    r"\boccidit\b\s+(.+?)(?:\s+(?:et\b|;|sicut|in\b|qui\b|de\b))",
    re.IGNORECASE | re.DOTALL,
)

# Appellee name between "appellavit" and "de morte/rapo/roberia/pace"
_APPELLEE_RE = re.compile(
    r"\bappellavit\b\s+(.+?)\s+de\s+(?:morte|rapo|roberia|pace)",
    re.IGNORECASE | re.DOTALL,
)


def _clean_name(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip(" ;,.'")[:80]


def _extract_party_1(plea_text: str) -> str:
    """Subject of the plea — everything before the first main verb."""
    # Strip the leading plea number
    text = re.sub(r"^\d+\S*\s*\.\s*", "", plea_text.strip(), count=1)
    m = _VERB_RE.search(text)
    if m and m.start() > 0:
        return _clean_name(text[:m.start()])
    return ""


def _extract_party_2(plea_text: str, offence_latin: str) -> str:
    """Victim (after occidit) or appellee (after appellavit), where detectable."""
    if "occidit" in offence_latin:
        m = _VICTIM_RE.search(plea_text)
        if m:
            return _clean_name(m.group(1))
    elif "appellavit" in offence_latin:
        m = _APPELLEE_RE.search(plea_text)
        if m:
            return _clean_name(m.group(1))
    return ""


# ---------------------------------------------------------------------------
# Offence detection
# ---------------------------------------------------------------------------

_OFFENCE_PATTERNS: list[tuple[str, str, str]] = [
    (r"suspendit\s+seipsum",               "suspendit seipsum",          "suicide"),
    (r"appellavit\b.{0,60}\bde\s+morte\b", "appellavit de morte",        "appeal-of-death"),
    (r"appellavit\b.{0,60}\bde\s+rap[ou]", "appellavit de rapo",         "appeal-of-rape"),
    (r"appellavit\b.{0,60}\bde\s+roberia", "appellavit de roberia",      "appeal-of-robbery"),
    (r"appellavit\b.{0,60}\bpace\b",       "appellavit de pace",         "appeal-of-breach-of-peace"),
    (r"occidit\b|occiderunt\b",            "occidit",                    "homicide"),
    (r"occis[au][sm]?\s+fuit\b",           "occisus/occisa fuit",        "homicide-unknown-killer"),
    (r"\blatron[ei]\b",                    "latro/latrones",             "robbery-brigandage"),
    (r"\broberia\b",                       "roberia",                    "robbery"),
    (r"\bfurt[io]\b",                      "furtum/furtis",              "theft"),
    (r"contra\s+assisam\b",                "contra assisam",             "assize-violation"),
    (r"assisa\b.{0,60}\bnon\s+est\s+servata", "assisa non servata",     "assize-violation"),
    (r"concelaverunt\b|concelavit\b",      "concelaverunt",              "concealment"),
    (r"ad\s+judicium\s+de\s+juratoribus",  "ad judicium de juratoribus", "jury-judgment"),
    (r"\bappellavit\b",                    "appellavit",                 "appeal-unspecified"),
]


def _detect_offence(text: str) -> tuple[str, str]:
    for pattern, label, otype in _OFFENCE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return label, otype
    return "", "unknown"


# ---------------------------------------------------------------------------
# Verdict detection
# ---------------------------------------------------------------------------

_VERDICT_PATTERNS: list[tuple[str, str]] = [
    (r"\bmurdrum\b",                                              "murdrum"),
    (r"\bsuspensus\b|\bsuspensa\b",                               "suspensus"),
    (r"exigatur\s+et\s+utlagetur\b",                              "exigatur et utlagetur"),
    (r"\butlagatus\s+est\b|\butlagata\s+est\b|\butlagetur\b",     "utlagatus est"),
    (r"\bquietus\s+est\b|\bquieta\s+est\b|\binde\s+quietus\b",   "quietus est"),
    (r"ponit\s+se\s+super\s+(patriam|juratam)",                   "ponit se super patriam"),
    (r"\bin\s+misericordia\b",                                    "in misericordia"),
    (r"\bcustodiatur\b|\bcommittitur\b",                          "custodiatur"),
    (r"\bloquendum\b",                                            "loquendum"),
    (r"\bnichil\b",                                               "nichil"),
]


def _detect_verdict(text: str) -> str:
    for pattern, label in _VERDICT_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return label
    return ""


# ---------------------------------------------------------------------------
# Amercement amount extraction
# ---------------------------------------------------------------------------

_AMOUNT_RE = re.compile(
    r"""
    (?:
        \d+\s*(?:m(?:arc[ae]?)?\b|™|")
      | \d+\s*(?:s(?:olid[io]s?)?\b|'\b|\^)
      | \d+\s*d(?:enari[io]s?)?\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _detect_amercement(text: str) -> str:
    hits = _AMOUNT_RE.findall(text)
    seen: set[str] = set()
    unique = []
    for h in hits:
        h = h.strip()
        if h not in seen:
            seen.add(h)
            unique.append(h)
    return "; ".join(unique)


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

@dataclass
class PleaRecord:
    membrane_ref: str
    plea_num: str
    hundred: str
    party_1: str
    party_2: str
    offence_latin: str
    offence_type: str
    verdict: str
    amercement_raw: str
    plea_text_snippet: str


def parse_pleas(text: str, membrane_ref: str) -> list[PleaRecord]:
    """Split Maitland text into numbered plea entries and extract fields."""
    location_map = _build_location_map(text)

    entry_re = re.compile(r"(?m)^\s*(\d+)\s*[\^²½⅓\]]*\s*\.")
    splits = [(m.start(), m.group(1)) for m in entry_re.finditer(text)]

    records = []
    for i, (start, num) in enumerate(splits):
        end = splits[i + 1][0] if i + 1 < len(splits) else len(text)
        plea_text = text[start:end].strip()

        hundred = _location_at(start, location_map)
        party_1 = _extract_party_1(plea_text)
        offence_latin, offence_type = _detect_offence(plea_text)
        party_2 = _extract_party_2(plea_text, offence_latin)
        verdict = _detect_verdict(plea_text)
        amercement = _detect_amercement(plea_text)
        snippet = re.sub(r"\s+", " ", plea_text)[:120]

        records.append(PleaRecord(
            membrane_ref=membrane_ref,
            plea_num=num,
            hundred=hundred,
            party_1=party_1,
            party_2=party_2,
            offence_latin=offence_latin,
            offence_type=offence_type,
            verdict=verdict,
            amercement_raw=amercement,
            plea_text_snippet=snippet,
        ))
    return records


def write_csv(records: list[PleaRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "membrane_ref", "plea_num", "hundred",
        "party_1", "party_2",
        "offence_latin", "offence_type",
        "verdict", "amercement_raw",
        "plea_text_snippet",
    ]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in records:
            writer.writerow({f: getattr(r, f) for f in fields})
