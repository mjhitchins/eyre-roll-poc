"""
Tests for Stage 6: SQLite collation and the hundred lat/lon summary join.
"""

import csv
import sqlite3

from src.collate.collator import (
    annotate_aalt_image,
    annotate_canonical_hundred,
    build_database,
    build_hundred_summary,
)


def _write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


PLEA_FIELDS = [
    "membrane_ref", "plea_num", "hundred", "party_1", "party_2",
    "offence_latin", "offence_type", "verdict", "amercement_raw",
    "plea_text_snippet",
]


class TestBuildDatabase:
    def test_counts_all_rows_across_files(self, tmp_path):
        csv1 = tmp_path / "m1_cases.csv"
        csv2 = tmp_path / "m2_cases.csv"
        _write_csv(csv1, [{"membrane_ref": "m1", "plea_num": "1", "hundred": "Berkelay"}], PLEA_FIELDS)
        _write_csv(csv2, [{"membrane_ref": "m2", "plea_num": "1", "hundred": ""}], PLEA_FIELDS)

        db_path = tmp_path / "test.db"
        count = build_database([csv1, csv2], db_path)

        assert count == 2
        con = sqlite3.connect(db_path)
        assert con.execute("SELECT COUNT(*) FROM pleas").fetchone()[0] == 2
        assert con.execute("SELECT plea_count FROM run_log").fetchone()[0] == 2


class TestAnnotateAaltImage:
    def test_fills_image_fields_for_every_plea_on_a_membrane(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [
                {"membrane_ref": "m1", "plea_num": "1", "hundred": ""},
                {"membrane_ref": "m1", "plea_num": "2", "hundred": ""},
            ],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        concordance_path = tmp_path / "concordance.csv"
        _write_csv(
            concordance_path,
            [{"membrane_ref": "m1", "tna_piece": "JUST 1/271",
              "aalt_image_url": "http://aalt.law.uh.edu/.../IMG_3855.htm",
              "aalt_image_filename": "IMG_3855", "maitland_section": "Memb. 1",
              "maitland_archive_id": "x", "coverage": "full",
              "verified": "yes", "confidence": "high", "notes": ""}],
            ["membrane_ref", "tna_piece", "aalt_image_url", "aalt_image_filename",
             "maitland_section", "maitland_archive_id", "coverage", "verified",
             "confidence", "notes"],
        )

        n = annotate_aalt_image(db_path, concordance_path)
        assert n == 1  # one membrane matched (both its pleas get updated)

        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT aalt_image_url, aalt_verified, aalt_confidence FROM pleas"
        ).fetchall()
        assert rows == [
            ("http://aalt.law.uh.edu/.../IMG_3855.htm", "yes", "high"),
            ("http://aalt.law.uh.edu/.../IMG_3855.htm", "yes", "high"),
        ]

    def test_membrane_missing_from_concordance_left_blank_not_guessed(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m99_cases.csv",
            [{"membrane_ref": "m99", "plea_num": "1", "hundred": ""}],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m99_cases.csv"], db_path)

        concordance_path = tmp_path / "concordance.csv"
        _write_csv(concordance_path, [], [
            "membrane_ref", "tna_piece", "aalt_image_url", "aalt_image_filename",
            "maitland_section", "maitland_archive_id", "coverage", "verified",
            "confidence", "notes",
        ])

        n = annotate_aalt_image(db_path, concordance_path)
        assert n == 0

        con = sqlite3.connect(db_path)
        assert con.execute("SELECT aalt_image_url FROM pleas").fetchone()[0] is None


class TestAnnotateCanonicalHundred:
    def test_fills_canonical_column_via_lookup(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [
                {"membrane_ref": "m1", "plea_num": "1", "hundred": "Berkelay"},
                {"membrane_ref": "m1", "plea_num": "2", "hundred": ""},
            ],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        lookup_path = tmp_path / "lookup.csv"
        _write_csv(
            lookup_path,
            [{"raw_value": "Berkelay", "membrane_refs": "m1", "canonical_hundred": "Berkeley",
              "confidence": "high", "note": ""}],
            ["raw_value", "membrane_refs", "canonical_hundred", "confidence", "note"],
        )

        n = annotate_canonical_hundred(db_path, lookup_path)
        assert n == 1  # only the non-blank row is touched

        con = sqlite3.connect(db_path)
        rows = con.execute(
            "SELECT plea_num, hundred_canonical FROM pleas ORDER BY plea_num"
        ).fetchall()
        assert rows == [("1", "Berkeley"), ("2", None)]

    def test_unmapped_raw_value_kept_visible_not_blanked(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [{"membrane_ref": "m1", "plea_num": "1", "hundred": "SomeNewHeading"}],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        lookup_path = tmp_path / "lookup.csv"
        _write_csv(lookup_path, [], ["raw_value", "membrane_refs", "canonical_hundred", "confidence", "note"])

        annotate_canonical_hundred(db_path, lookup_path)

        con = sqlite3.connect(db_path)
        assert con.execute("SELECT hundred_canonical FROM pleas").fetchone()[0] == "SomeNewHeading"


class TestBuildHundredSummary:
    def test_joins_lookup_and_coords_and_aggregates(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [
                {"membrane_ref": "m1", "plea_num": "1", "hundred": "Berkelay"},
                {"membrane_ref": "m1", "plea_num": "2", "hundred": "Berkdcge"},  # same hundred, OCR variant
                {"membrane_ref": "m1", "plea_num": "3", "hundred": ""},         # no heading — excluded
            ],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        lookup_path = tmp_path / "lookup.csv"
        _write_csv(
            lookup_path,
            [
                {"raw_value": "Berkelay", "membrane_refs": "m1", "canonical_hundred": "Berkeley",
                 "confidence": "high", "note": ""},
                {"raw_value": "Berkdcge", "membrane_refs": "m1", "canonical_hundred": "Berkeley",
                 "confidence": "high", "note": ""},
            ],
            ["raw_value", "membrane_refs", "canonical_hundred", "confidence", "note"],
        )

        coords_path = tmp_path / "coords.csv"
        _write_csv(
            coords_path,
            [{"canonical_hundred": "Berkeley", "lat": "51.69", "lon": "-2.46",
              "proxy_place": "Berkeley", "source_note": "chief town"}],
            ["canonical_hundred", "lat", "lon", "proxy_place", "source_note"],
        )

        out_path = tmp_path / "hundreds.csv"
        summary = build_hundred_summary(db_path, lookup_path, coords_path, out_path)

        assert len(summary) == 1
        row = summary[0]
        assert row["canonical_hundred"] == "Berkeley"
        assert row["raw_values"] == "Berkdcge; Berkelay"
        assert row["plea_count"] == 2
        assert row["status"] == "mapped"
        assert row["lat"] == "51.69"
        assert out_path.exists()

    def test_unresolved_hundred_kept_with_blank_coordinates(self, tmp_path):
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [{"membrane_ref": "m1", "plea_num": "1", "hundred": "Bernetre Hambyria"}],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        lookup_path = tmp_path / "lookup.csv"
        _write_csv(
            lookup_path,
            [{"raw_value": "Bernetre Hambyria", "membrane_refs": "m1",
              "canonical_hundred": "UNIDENTIFIED", "confidence": "low", "note": ""}],
            ["raw_value", "membrane_refs", "canonical_hundred", "confidence", "note"],
        )
        coords_path = tmp_path / "coords.csv"
        _write_csv(coords_path, [], ["canonical_hundred", "lat", "lon", "proxy_place", "source_note"])

        out_path = tmp_path / "hundreds.csv"
        summary = build_hundred_summary(db_path, lookup_path, coords_path, out_path)

        assert summary == [{
            "canonical_hundred": "UNIDENTIFIED", "raw_values": "Bernetre Hambyria",
            "plea_count": 1, "status": "unresolved",
            "lat": "", "lon": "", "proxy_place": "", "source_note": "",
        }]

    def test_raw_value_missing_from_lookup_is_flagged_not_dropped(self, tmp_path):
        # Guards against a future membrane introducing a new heading spelling
        # that nobody has added to data/hundred_lookup.csv yet — it must show
        # up as visibly unresolved, not silently vanish from the map/report.
        db_path = tmp_path / "test.db"
        _write_csv(
            tmp_path / "m1_cases.csv",
            [{"membrane_ref": "m1", "plea_num": "1", "hundred": "SomeNewHeading"}],
            PLEA_FIELDS,
        )
        build_database([tmp_path / "m1_cases.csv"], db_path)

        lookup_path = tmp_path / "lookup.csv"
        _write_csv(lookup_path, [], ["raw_value", "membrane_refs", "canonical_hundred", "confidence", "note"])
        coords_path = tmp_path / "coords.csv"
        _write_csv(coords_path, [], ["canonical_hundred", "lat", "lon", "proxy_place", "source_note"])

        out_path = tmp_path / "hundreds.csv"
        summary = build_hundred_summary(db_path, lookup_path, coords_path, out_path)

        assert len(summary) == 1
        assert summary[0]["status"] == "unresolved"
        assert "SomeNewHeading" in summary[0]["canonical_hundred"]
