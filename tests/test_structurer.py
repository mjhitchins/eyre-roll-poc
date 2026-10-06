"""
Tests for Stage 5: structured-field extraction from Maitland ground-truth text.

The hundred-heading detection is the trickiest part of this stage — the OCR'd
"Hundredum"/"Hundredo" token is corrupted differently almost every time it
appears, and the detector has to tell a genuine section heading apart from
narrative text that happens to look like one. Each false positive below is a
real line pulled from the ground-truth corpus (see data/ground_truth/), not a
hypothetical.
"""

from src.structure.structurer import _build_location_map, parse_pleas


# ---------------------------------------------------------------------------
# Hundred heading detection — true positives (real OCR variants seen)
# ---------------------------------------------------------------------------

class TestHundredHeadingVariants:
    def test_plain_heading(self):
        text = "Htmdredum de Kyftesiatc.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Kyftesiatc"]

    def test_continuation_marker(self):
        text = "Adhuc de Hundredo de Slochtre.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Slochtre"]

    def test_continuation_with_hundredum_token_dropped(self):
        # "Adhiic de Stvinesheved." — OCR dropped the "Hundredo" word entirely
        text = "Adhiic de Stvinesheved.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Stvinesheved"]

    def test_missing_second_de(self):
        # "Adhiic de Hundredo TJieokesbirie." — OCR dropped the second "de"
        text = "Adhiic de Hundredo TJieokesbirie.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["TJieokesbirie"]

    def test_compound_hundred_name(self):
        # a joint session heading naming two hundreds
        text = "Hundrediim'^ de Holeford et de Gretestan.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Holeford et de Gretestan"]

    def test_ad_hue_variant(self):
        # "Adhuc" OCR'd as two words, "Hundredo" OCR'd past recognition
        text = "Ad hue de Hiindrcdo de Berkdcge.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Berkdcge"]

    def test_opening_villata_heading(self):
        # m27.txt opens with "Villata de Thornebiric." standing in for the
        # usual hundred heading — only valid as the file's first line.
        text = "Villata de Thornebiric.\n\n1. Willelmus occidit.\n"
        assert [n for _, n in _build_location_map(text)] == ["Thornebiric"]


# ---------------------------------------------------------------------------
# Hundred heading detection — false positives that must NOT match
# ---------------------------------------------------------------------------

class TestHundredHeadingFalsePositives:
    def test_narrative_hue_and_cry_phrase(self):
        # real line from m30.txt: not a heading, a hue-and-cry narrative
        # phrase inside a plea ("the Hundred of Hanbiria pursued him...")
        text = (
            "1. Quidam homo fugit in eccle-\n"
            "siam ; et inde evasit; et Hundredum de\n"
            "Hanbiria secutus fuit eum cum clamore usque ad villam\n"
            "illam ; et villata hoc cognovit.\n"
        )
        assert _build_location_map(text) == []

    def test_vill_subheading_does_not_override_hundred(self):
        # a vill sub-section must not be captured as a (pseudo-)hundred
        text = (
            "Hundredum de Berkelay.\n\n"
            "1. Willelmus occidit.\n\n"
            "Villata de Neivenham.\n\n"
            "2. Robertus occidit.\n"
        )
        locs = _build_location_map(text)
        assert [n for _, n in locs] == ["Berkelay"]

    def test_manuscript_variant_footnote(self):
        # real line from m25.txt: "B" refers to a second manuscript copy,
        # not a hundred — "hachia" is lowercase body text, not a heading
        text = "1. Willelmus fecit hachia B.\n"
        assert _build_location_map(text) == []

    def test_wrapped_juror_name_list(self):
        # real line from m24.txt: the tail of a wrapped list of juror names
        # ("..., Rannulfus de Quentone, Henricus de Monte ^.") happens to
        # land alone on its own line, syntactically identical to a heading —
        # the preceding line's trailing comma is what rules it out.
        text = (
            "125. Inquiratur de catallis.\n\n"
            "Cloptone, Johannes de Welleforde, Willelmus de Quentone,\n"
            "Rannulfus de Quentone, Henricus de Monte ^.\n\n"
            "126. Emma appellavit.\n"
        )
        assert _build_location_map(text) == []


# ---------------------------------------------------------------------------
# End-to-end: hundred field on parsed plea records
# ---------------------------------------------------------------------------

class TestParsePleasHundredField:
    def test_plea_inherits_most_recent_hundred(self):
        text = (
            "Hundredum de Berkelay.\n\n"
            "1. Willelmus occidit Robertum.\n\n"
            "Adhuc de Hundredo de Slochtre.\n\n"
            "2. Johannes occidit Henricum.\n"
        )
        records = parse_pleas(text, membrane_ref="m99")
        hundreds = {r.plea_num: r.hundred for r in records}
        assert hundreds == {"1": "Berkelay", "2": "Slochtre"}

    def test_plea_before_any_heading_is_blank(self):
        text = "1. Willelmus occidit Robertum.\n\nHundredum de Berkelay.\n\n2. Johannes occidit.\n"
        records = parse_pleas(text, membrane_ref="m99")
        assert records[0].hundred == ""
        assert records[1].hundred == "Berkelay"
