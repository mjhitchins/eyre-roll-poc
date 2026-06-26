"""
Kraken HTR adapter for Stage 3 transcription.

Replaces the Anthropic API backend with Kraken, a free open-source HTR
engine designed for historical manuscripts.  No API key or subscription
needed — inference runs locally on CPU.

Workflow per image:
  1. Open image and binarize (Kraken's non-linear binarization)
  2. Segment into text lines (heuristic, no separate segmentation model needed)
  3. Run HTR recognition model over each line
  4. Emit numbered lines matching the reading order returned by the segmenter

The caller is responsible for downloading a suitable .mlmodel file and
passing its path here (see MODELS.md for recommendations).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image
from kraken import binarization, pageseg
from kraken.lib import models
import kraken.rpred as rpred


def transcribe_image(
    image_path: Path,
    model_path: Path,
    **kwargs,
) -> dict:
    """
    Run Kraken HTR on image_path using the model at model_path.

    Returns a dict with:
        transcript  — numbered lines of recognised Latin text
        model       — absolute path to the model file used
        stop_reason — always "end_turn" (kept for interface compatibility)
        usage       — always zeroed (no token billing)
    """
    image_path = Path(image_path)
    model_path = Path(model_path)

    if not model_path.exists():
        raise FileNotFoundError(
            f"Kraken model not found: {model_path}\n"
            "Download a model first — see MODELS.md for instructions."
        )

    net = models.load_any(str(model_path), device="cpu")

    im = Image.open(image_path)
    # nlbin expects greyscale or binary; convert if needed
    if im.mode not in ("1", "L"):
        im = im.convert("L")

    bim = binarization.nlbin(im)
    seg = pageseg.segment(bim)

    lines = [record.prediction for record in rpred.rpred(net, bim, seg)]
    transcript = "\n".join(f"{i + 1}  {line}" for i, line in enumerate(lines))

    return {
        "transcript": transcript,
        "model": str(model_path.resolve()),
        "stop_reason": "end_turn",
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }
