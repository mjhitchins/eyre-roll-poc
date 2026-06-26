"""
Stage 3: Transcribe preprocessed membrane images to Latin text using Kraken HTR.

Input:  data/images_clean/{membrane_ref}.jpg
Output: output/transcripts/{membrane_ref}.txt
        output/transcripts/{membrane_ref}_manifest.json

Each run writes a manifest alongside the transcript recording the exact
parameters used (model path, image path, timestamp) so results are
reproducible and citable.

Idempotent: if the transcript already exists and force=False the function
returns immediately with skipped=True rather than re-running inference.

Abbreviation conventions used in the prompt reference files
(src/transcribe/prompts/v1_diplomatic.txt) are documented for human
reviewers post-transcription; Kraken applies its trained model directly
and does not interpret a text prompt.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from .model_client import transcribe_image

logger = logging.getLogger(__name__)


def transcribe_membrane(
    membrane_ref: str,
    clean_image_path: Path,
    output_dir: Path,
    model_path: Path,
    force: bool = False,
) -> dict:
    """
    Transcribe one membrane image to Latin text.

    Returns a record dict describing the run (or the skipped state).
    """
    clean_image_path = Path(clean_image_path)
    output_dir = Path(output_dir)
    model_path = Path(model_path)

    transcript_path = output_dir / f"{membrane_ref}.txt"
    manifest_path = output_dir / f"{membrane_ref}_manifest.json"

    if transcript_path.exists() and not force:
        logger.info("Transcript exists, skipping: %s", transcript_path)
        return {
            "skipped": True,
            "membrane_ref": membrane_ref,
            "transcript_path": str(transcript_path),
        }

    if not clean_image_path.exists():
        raise FileNotFoundError(
            f"Clean image not found: {clean_image_path}. "
            "Run Stage 2 (preprocess) first."
        )

    logger.info("Transcribing %s with model=%s", membrane_ref, model_path.name)

    result = transcribe_image(
        image_path=clean_image_path,
        model_path=model_path,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(result["transcript"], encoding="utf-8")
    logger.info(
        "Transcript saved: %s (%d chars)",
        transcript_path, len(result["transcript"]),
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    manifest = {
        "timestamp_utc": ts,
        "membrane_ref": membrane_ref,
        "source_image": str(clean_image_path),
        "transcript_path": str(transcript_path),
        "model": result["model"],
        "stop_reason": result["stop_reason"],
        "usage": result["usage"],
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Manifest written: %s", manifest_path)

    return {
        "skipped": False,
        "membrane_ref": membrane_ref,
        "transcript_path": str(transcript_path),
        "manifest_path": str(manifest_path),
        **manifest,
    }
