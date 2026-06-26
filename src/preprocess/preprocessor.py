"""
Stage 2: Preprocess raw AALT JPEG images for transcription.

Pipeline per image:
  1. Load as BGR, convert to greyscale
  2. CLAHE contrast normalisation (handles uneven parchment illumination)
  3. Deskew — rotate to make text lines horizontal
  4. Conservative crop to text block

Raw images are never modified. All output goes to data/images_clean/.
Operations are idempotent: if the output file already exists it is not
reprocessed (caller should delete it to force a redo).

Deskew method: horizontal-projection variance maximisation over a search
range of ±10°. This is more robust on parchment than Hough lines because
medieval court hand does not produce clean long straight strokes that
Hough can anchor on. The projection method finds the angle at which
horizontal slices of the image have the highest variance (= text lines
are sharpest when the page is level).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# Default parameters — record these in every manifest so runs are reproducible
DEFAULT_CLAHE_CLIP = 2.0
DEFAULT_CLAHE_TILE = 8
DEFAULT_CROP_BORDER = 0.02   # strip 2 % of each edge before content detection
DESKEW_SEARCH_DEG = 10.0     # search ±10° around horizontal
DESKEW_STEP_DEG = 0.25       # angular resolution of the search


def _load(path: Path) -> np.ndarray:
    img = cv2.imread(str(path))
    if img is None:
        raise ValueError(f"cv2.imread could not read: {path}")
    return img


def to_greyscale(img: np.ndarray) -> np.ndarray:
    if img.ndim == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def apply_clahe(
    grey: np.ndarray,
    clip_limit: float = DEFAULT_CLAHE_CLIP,
    tile_size: int = DEFAULT_CLAHE_TILE,
) -> np.ndarray:
    clahe = cv2.createCLAHE(
        clipLimit=clip_limit,
        tileGridSize=(tile_size, tile_size),
    )
    return clahe.apply(grey)


def _projection_variance(grey: np.ndarray, angle_deg: float) -> float:
    """Rotate grey by angle_deg and return variance of row sums."""
    h, w = grey.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    rotated = cv2.warpAffine(
        grey, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=255
    )
    row_sums = rotated.sum(axis=1).astype(np.float64)
    return float(np.var(row_sums))


def estimate_skew_angle(
    grey: np.ndarray,
    search_range: float = DESKEW_SEARCH_DEG,
    step: float = DESKEW_STEP_DEG,
) -> float:
    """
    Return the skew angle (degrees) that maximises horizontal-projection
    variance. Positive angle = image is rotated counter-clockwise relative
    to level; rotating by +angle corrects it.
    """
    angles = np.arange(-search_range, search_range + step, step)
    variances = [_projection_variance(grey, a) for a in angles]
    best_angle = float(angles[int(np.argmax(variances))])
    logger.debug("Skew estimate: %.2f° (searched ±%.1f°)", best_angle, search_range)
    return best_angle


def deskew(grey: np.ndarray, angle_deg: float) -> np.ndarray:
    if abs(angle_deg) < 0.1:
        return grey
    h, w = grey.shape
    M = cv2.getRotationMatrix2D((w / 2, h / 2), angle_deg, 1.0)
    return cv2.warpAffine(
        grey, M, (w, h), flags=cv2.INTER_LINEAR, borderValue=255
    )


def crop_to_content(grey: np.ndarray, border_fraction: float = DEFAULT_CROP_BORDER) -> np.ndarray:
    """
    Strip a hard border fraction, then tighten to the bounding box of dark
    (ink) pixels with a small margin. This removes membrane edges and
    photography background without risk of cutting into the text.
    """
    h, w = grey.shape
    bh = int(h * border_fraction)
    bw = int(w * border_fraction)
    trimmed = grey[bh: h - bh, bw: w - bw]

    _, binary = cv2.threshold(trimmed, 200, 255, cv2.THRESH_BINARY_INV)
    coords = cv2.findNonZero(binary)
    if coords is None:
        return trimmed

    x, y, cw, ch = cv2.boundingRect(coords)
    margin = 30
    x = max(0, x - margin)
    y = max(0, y - margin)
    x2 = min(trimmed.shape[1], x + cw + 2 * margin)
    y2 = min(trimmed.shape[0], y + ch + 2 * margin)
    return trimmed[y:y2, x:x2]


def preprocess_image(
    input_path: Path,
    output_path: Path,
    clahe_clip: float = DEFAULT_CLAHE_CLIP,
    clahe_tile: int = DEFAULT_CLAHE_TILE,
    crop_border: float = DEFAULT_CROP_BORDER,
    force: bool = False,
) -> dict:
    """
    Preprocess one membrane image. Returns a params dict for the run manifest.

    Skips processing and returns the existing record if output_path already
    exists and force=False (idempotent).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if output_path.exists() and not force:
        logger.info("Already preprocessed, skipping: %s", output_path)
        return {"skipped": True, "output": str(output_path)}

    img = _load(input_path)
    grey = to_greyscale(img)
    enhanced = apply_clahe(grey, clip_limit=clahe_clip, tile_size=clahe_tile)
    angle = estimate_skew_angle(enhanced)
    deskewed = deskew(enhanced, angle)
    final = crop_to_content(deskewed, border_fraction=crop_border)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ok = cv2.imwrite(str(output_path), final)
    if not ok:
        raise RuntimeError(f"cv2.imwrite failed for {output_path}")

    params = {
        "skipped": False,
        "input": str(input_path),
        "output": str(output_path),
        "input_shape_hwc": list(img.shape),
        "output_shape_hw": list(final.shape),
        "skew_angle_deg": round(angle, 3),
        "clahe_clip": clahe_clip,
        "clahe_tile": clahe_tile,
        "crop_border_fraction": crop_border,
    }
    logger.info(
        "Preprocessed %s → %s (skew=%.2f°, out %dx%d)",
        input_path.name,
        output_path.name,
        angle,
        final.shape[1],
        final.shape[0],
    )
    return params


def write_manifest(records: list[dict], output_dir: Path) -> Path:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"preprocess_manifest_{ts}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {"timestamp": ts, "records": records},
            indent=2,
        )
    )
    logger.info("Manifest written: %s", path)
    return path
