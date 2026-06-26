"""
CER/WER scorer for model transcriptions vs Maitland ground truth.

Usage:
    from src.score.scorer import score
    result = score(hypothesis="...", reference="...")
    print(result.cer, result.wer)
"""

from dataclasses import dataclass, field
from typing import Optional

import jiwer

from .normalise import normalise, NORMALISATION_DESCRIPTION


@dataclass
class ScoreResult:
    cer: float          # character error rate (0.0–1.0+)
    wer: float          # word error rate (0.0–1.0+)
    ref_chars: int      # character count in normalised reference
    hyp_chars: int      # character count in normalised hypothesis
    ref_words: int      # word count in normalised reference
    hyp_words: int      # word count in normalised hypothesis
    membrane_ref: Optional[str] = None
    normalisation: str = NORMALISATION_DESCRIPTION

    def summary_line(self) -> str:
        return (
            f"CER={self.cer:.3f}  WER={self.wer:.3f}  "
            f"(ref {self.ref_words}w/{self.ref_chars}c  "
            f"hyp {self.hyp_words}w/{self.hyp_chars}c)"
        )


def score(hypothesis: str, reference: str, membrane_ref: Optional[str] = None) -> ScoreResult:
    """
    Score a model transcript against a Maitland ground-truth passage.

    Both texts are normalised identically before comparison (see normalise.py).
    CER is computed character-by-character; WER word-by-word.

    Args:
        hypothesis:   model transcription
        reference:    Maitland ground-truth text for the same membrane
        membrane_ref: optional provenance label (membrane id) for the report

    Returns:
        ScoreResult with CER, WER, and token counts
    """
    h = normalise(hypothesis)
    r = normalise(reference)

    # jiwer.cer / jiwer.wer expect (reference, hypothesis)
    cer = jiwer.cer(r, h)
    wer = jiwer.wer(r, h)

    # Character counts (excluding spaces, which are alignment artefacts)
    ref_chars = len(r.replace(" ", ""))
    hyp_chars = len(h.replace(" ", ""))

    return ScoreResult(
        cer=cer,
        wer=wer,
        ref_chars=ref_chars,
        hyp_chars=hyp_chars,
        ref_words=len(r.split()) if r else 0,
        hyp_words=len(h.split()) if h else 0,
        membrane_ref=membrane_ref,
    )
