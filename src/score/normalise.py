"""
Text normalisation for medieval Latin CER/WER comparison.

Applied symmetrically to BOTH the model transcript and the Maitland ground
truth before any score is computed. The normalisation choices are documented
here because changing them changes the reported number — state them whenever
reporting a score.

Current normalisation (v1):
  1. Unicode NFC normalisation
  2. Lowercase
  3. u → v  (medieval scribes used u/v interchangeably; 'uilla' = 'villa')
  4. j → i  (medieval scribes used i/j interchangeably; 'iusticiarius' = 'justiciarius')
  5. Strip punctuation (keep letters, digits, spaces)
  6. Collapse whitespace
"""

import re
import unicodedata

NORMALISATION_DESCRIPTION = (
    "lowercase; u→v; j→i; punctuation stripped; whitespace collapsed (v1)"
)


def normalise(text: str) -> str:
    """Normalise medieval Latin text for error-rate comparison."""
    text = unicodedata.normalize("NFC", text)
    text = text.lower()
    # u/v interchange: map both to v (the consonantal/modern form)
    text = text.replace("u", "v")
    # i/j interchange: map both to i
    text = text.replace("j", "i")
    # Keep only word characters and spaces; strip punctuation
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse runs of whitespace to a single space
    text = re.sub(r"\s+", " ", text).strip()
    return text
