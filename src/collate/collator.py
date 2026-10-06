"""
Stage 6: Collate structured case CSVs into a single SQLite database.

Reads all output/metrics/*_cases.csv files and writes output/eyre1221.db.
The database is the canonical output for the publish stage and analysis.

Tables:
  pleas    — one row per plea entry
  run_log  — build metadata (timestamp, membranes included, plea count)

Also builds output/hundreds.csv: raw "hundred" manuscript spellings, grouped
into the canonical historic hundred they refer to and (where known) an
approximate map coordinate — see data/hundred_lookup.csv and
data/hundred_coords.csv, both hand-curated and source-noted. This join is
recomputed fresh from the current database every run, rather than caching
plea counts in a hand-edited file, so the map never goes stale relative to
the pipeline's actual output.

Also joins each plea to its source AALT manuscript image via
data/concordance.csv (membrane_ref -> aalt_image_url), per CONCORDANCE.md.
Only one membrane (m24) has passed the V3 spot-check (verified=yes); every
other row is an arithmetic extrapolation from that single anchor
(verified=pending) and must be presented as such, never as settled fact —
see CONCORDANCE.md's "three verifications" and the `verified`/`confidence`
columns this carries through to pleas.aalt_verified/aalt_confidence.
"""

from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS pleas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    membrane_ref      TEXT NOT NULL,
    plea_num          TEXT,
    hundred           TEXT,
    hundred_canonical TEXT,
    aalt_image_url    TEXT,
    aalt_verified     TEXT,
    aalt_confidence   TEXT,
    party_1           TEXT,
    party_2           TEXT,
    offence_latin     TEXT,
    offence_type      TEXT,
    verdict           TEXT,
    amercement_raw    TEXT,
    plea_text_snippet TEXT
);

CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    built_at    TEXT NOT NULL,
    membranes   TEXT NOT NULL,
    plea_count  INTEGER NOT NULL
);
"""

_PLEA_FIELDS = [
    "membrane_ref", "plea_num", "hundred",
    "party_1", "party_2",
    "offence_latin", "offence_type",
    "verdict", "amercement_raw",
    "plea_text_snippet",
]


def build_database(csv_paths: list[Path], db_path: Path) -> int:
    """Build (or rebuild) the SQLite database from a list of case CSV paths."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    con = sqlite3.connect(db_path)
    con.executescript(_SCHEMA)

    all_rows: list[dict] = []
    membranes_seen: list[str] = []

    for csv_path in sorted(csv_paths):
        with csv_path.open(encoding="utf-8", newline="") as f:
            rows = list(csv.DictReader(f))
        all_rows.extend(rows)
        if rows:
            ref = rows[0].get("membrane_ref", csv_path.stem.replace("_cases", ""))
            if ref not in membranes_seen:
                membranes_seen.append(ref)

    placeholders = ", ".join("?" * len(_PLEA_FIELDS))
    con.executemany(
        f"INSERT INTO pleas ({', '.join(_PLEA_FIELDS)}) VALUES ({placeholders})",
        [[r.get(f, "") for f in _PLEA_FIELDS] for r in all_rows],
    )

    con.execute(
        "INSERT INTO run_log (built_at, membranes, plea_count) VALUES (?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            ", ".join(membranes_seen),
            len(all_rows),
        ),
    )

    con.commit()
    con.close()
    return len(all_rows)


_HUNDRED_SUMMARY_FIELDS = [
    "canonical_hundred", "plea_count", "status",
    "lat", "lon", "proxy_place", "source_note",
]


def _load_hundred_lookup(lookup_path: Path) -> dict[str, str]:
    lookup: dict[str, str] = {}
    with lookup_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            lookup[row["raw_value"]] = row["canonical_hundred"]
    return lookup


def annotate_canonical_hundred(db_path: Path, lookup_path: Path) -> int:
    """
    Populate pleas.hundred_canonical from the raw hundred field via
    data/hundred_lookup.csv, so client code (e.g. the docs/ map) can filter
    or join on the identified hundred without re-implementing the lookup.

    A raw value with no lookup entry is left as the literal raw value
    (visibly distinct/unresolved, never silently blanked) — same policy as
    build_hundred_summary.
    """
    lookup = _load_hundred_lookup(lookup_path)

    con = sqlite3.connect(db_path)
    rows = con.execute("SELECT id, hundred FROM pleas WHERE hundred != ''").fetchall()
    con.executemany(
        "UPDATE pleas SET hundred_canonical = ? WHERE id = ?",
        [(lookup.get(raw, raw), pid) for pid, raw in rows],
    )
    con.commit()
    con.close()
    return len(rows)


def annotate_aalt_image(db_path: Path, concordance_path: Path) -> int:
    """
    Populate pleas.aalt_image_url/aalt_verified/aalt_confidence from
    data/concordance.csv, joined on membrane_ref — "linking a plea to the
    image it is on" per CONCORDANCE.md.

    A membrane missing from the concordance is left with NULL/blank image
    fields rather than guessed — never fabricate a plausible-looking AALT
    URL for a membrane that hasn't actually been mapped.
    """
    concordance: dict[str, dict] = {}
    with concordance_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            concordance[row["membrane_ref"]] = row

    con = sqlite3.connect(db_path)
    membrane_refs = [r[0] for r in con.execute("SELECT DISTINCT membrane_ref FROM pleas")]
    updates = []
    for ref in membrane_refs:
        row = concordance.get(ref)
        if row is None:
            continue
        updates.append((row["aalt_image_url"], row["verified"], row["confidence"], ref))
    con.executemany(
        "UPDATE pleas SET aalt_image_url = ?, aalt_verified = ?, aalt_confidence = ? "
        "WHERE membrane_ref = ?",
        updates,
    )
    con.commit()
    con.close()
    return len(updates)


def build_hundred_summary(
    db_path: Path, lookup_path: Path, coords_path: Path, out_path: Path
) -> list[dict]:
    """
    Group plea counts by canonical historic hundred and attach a map
    coordinate where one is known.

    raw "hundred" value --(data/hundred_lookup.csv)--> canonical hundred
                         --(data/hundred_coords.csv)--> lat/lon (if known)

    A raw value missing from the lookup, or a canonical hundred missing from
    the coordinates table, is still included in the output with
    status="unresolved" and blank lat/lon — it is never silently dropped or
    given a guessed location.
    """
    lookup = _load_hundred_lookup(lookup_path)

    coords: dict[str, dict] = {}
    with coords_path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            coords[row["canonical_hundred"]] = row

    con = sqlite3.connect(db_path)
    raw_counts = con.execute(
        "SELECT hundred, COUNT(*) AS n FROM pleas WHERE hundred != '' GROUP BY hundred"
    ).fetchall()
    con.close()

    totals: dict[str, int] = {}
    for raw_hundred, n in raw_counts:
        canonical = lookup.get(raw_hundred, f"UNMAPPED RAW VALUE: {raw_hundred}")
        totals[canonical] = totals.get(canonical, 0) + n

    summary = []
    for canonical, plea_count in sorted(totals.items(), key=lambda kv: -kv[1]):
        coord = coords.get(canonical)
        summary.append({
            "canonical_hundred": canonical,
            "plea_count": plea_count,
            "status": "mapped" if coord else "unresolved",
            "lat": coord["lat"] if coord else "",
            "lon": coord["lon"] if coord else "",
            "proxy_place": coord["proxy_place"] if coord else "",
            "source_note": coord["source_note"] if coord else "",
        })

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_HUNDRED_SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary)

    return summary
