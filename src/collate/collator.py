"""
Stage 6: Collate structured case CSVs into a single SQLite database.

Reads all output/metrics/*_cases.csv files and writes output/eyre1221.db.
The database is the canonical output for the publish stage and analysis.

Tables:
  pleas    — one row per plea entry
  run_log  — build metadata (timestamp, membranes included, plea count)
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
