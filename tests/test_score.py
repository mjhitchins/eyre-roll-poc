"""
Tests for Stage 4: CER/WER scorer and normaliser.

Uses hand-crafted string pairs with known expected outputs so that
the measurement loop is proven independently of any model transcription.
"""

import pytest

from src.score.normalise import normalise
from src.score.scorer import score


# ---------------------------------------------------------------------------
# Normaliser tests
# ---------------------------------------------------------------------------

class TestNormalise:
    def test_lowercase(self):
        assert normalise("Robertus") == "robertvs"

    def test_u_to_v(self):
        # 'uilla' is medieval Latin for 'villa'
        assert normalise("uilla") == "villa"
        # i-u-s-t-i-c-i-a-r-i-u-s → u→v → i-v-s-t-i-c-i-a-r-i-v-s
        assert normalise("iusticiarius") == "ivsticiarivs"

    def test_j_to_i(self):
        assert normalise("justicia") == "ivsticia"

    def test_u_and_j_together(self):
        # u→v first, then j→i; order must not matter since they are disjoint
        assert normalise("Justitia") == "ivstitia"

    def test_punctuation_stripped(self):
        assert normalise("et. in.") == "et in"

    def test_whitespace_collapsed(self):
        # W is not u/v, so 'Willelmus' → 'willelmvs' (only the u→v)
        assert normalise("  Willelmus   de   Bosco  ") == "willelmvs de bosco"

    def test_empty_string(self):
        assert normalise("") == ""

    def test_symmetric_on_identical_text(self):
        text = "Hugo filius Willelmi"
        assert normalise(text) == normalise(text)


# ---------------------------------------------------------------------------
# Scorer tests — known string pairs with analytically predictable outputs
# ---------------------------------------------------------------------------

class TestScore:
    def test_identical_strings_give_zero_error(self):
        text = "Willelmus occidit Rogerum"
        result = score(text, text)
        assert result.cer == pytest.approx(0.0)
        assert result.wer == pytest.approx(0.0)

    def test_empty_hypothesis_gives_error_rate_one(self):
        result = score(hypothesis="", reference="Willelmus")
        assert result.wer == pytest.approx(1.0)
        assert result.cer == pytest.approx(1.0)

    def test_single_character_substitution_cer(self):
        # After normalisation both are single tokens with one char difference
        # ref = "aaa", hyp = "aab" → 1 substitution in 3 chars → CER = 1/3
        result = score(hypothesis="aab", reference="aaa")
        assert result.cer == pytest.approx(1 / 3, abs=0.01)

    def test_single_word_substitution_wer(self):
        # ref = "willelmus occidit rogerum" (3 words)
        # hyp = "willelmus occidit iohannem" (1 substitution)
        # WER = 1/3
        result = score(
            hypothesis="Willelmus occidit Iohannem",
            reference="Willelmus occidit Rogerum",
        )
        assert result.wer == pytest.approx(1 / 3, abs=0.01)

    def test_u_v_normalisation_reduces_error(self):
        # 'uilla' and 'villa' should score as identical after normalisation
        result = score(hypothesis="uilla", reference="villa")
        assert result.cer == pytest.approx(0.0)
        assert result.wer == pytest.approx(0.0)

    def test_i_j_normalisation_reduces_error(self):
        # 'iusticia' and 'justicia' should score as identical
        result = score(hypothesis="justicia", reference="iusticia")
        assert result.cer == pytest.approx(0.0)
        assert result.wer == pytest.approx(0.0)

    def test_case_normalisation_reduces_error(self):
        result = score(hypothesis="WILLELMUS", reference="willelmus")
        assert result.cer == pytest.approx(0.0)

    def test_membrane_ref_is_preserved(self):
        result = score("foo", "foo", membrane_ref="m1")
        assert result.membrane_ref == "m1"

    def test_result_has_word_counts(self):
        result = score(
            hypothesis="Willelmus de Bosco",
            reference="Willelmus de Bosco",
        )
        assert result.ref_words == 3
        assert result.hyp_words == 3

    def test_completely_wrong_transcript(self):
        # Gibberish vs real Latin — CER and WER should be high (>0.5)
        result = score(
            hypothesis="zzz qqq xxx yyy",
            reference="Willelmus occidit Rogerum et fugit",
        )
        assert result.wer > 0.5
        assert result.cer > 0.5

    def test_summary_line_contains_cer_and_wer(self):
        result = score("abc", "abc")
        line = result.summary_line()
        assert "CER=" in line
        assert "WER=" in line
