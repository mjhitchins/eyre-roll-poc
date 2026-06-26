"""
Tests for Stage 2: image preprocessor.

Uses synthetic images (no real AALT download needed) to test the
preprocessing operations and the idempotence contract.
"""

import numpy as np
import cv2
import pytest
from pathlib import Path

from src.preprocess.preprocessor import (
    to_greyscale,
    apply_clahe,
    estimate_skew_angle,
    deskew,
    crop_to_content,
    preprocess_image,
)


# ---------------------------------------------------------------------------
# Helpers: synthetic image fixtures
# ---------------------------------------------------------------------------

def make_grey_image(h: int = 200, w: int = 300, value: int = 200) -> np.ndarray:
    """Uniform grey image."""
    return np.full((h, w), value, dtype=np.uint8)


def make_bgr_image(h: int = 200, w: int = 300) -> np.ndarray:
    """Random-ish BGR image."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, (h, w, 3), dtype=np.uint8)


def make_text_like_image(h: int = 400, w: int = 600) -> np.ndarray:
    """
    Synthetic 'document' image: white background with dark horizontal bands
    simulating lines of text. Used to test deskew angle estimation.
    """
    img = np.full((h, w), 240, dtype=np.uint8)
    for row in range(50, h - 50, 40):
        img[row: row + 8, 40: w - 40] = 30
    return img


# ---------------------------------------------------------------------------
# to_greyscale
# ---------------------------------------------------------------------------

class TestToGreyscale:
    def test_bgr_becomes_2d(self):
        bgr = make_bgr_image()
        grey = to_greyscale(bgr)
        assert grey.ndim == 2

    def test_already_grey_unchanged(self):
        grey = make_grey_image()
        out = to_greyscale(grey)
        assert out.ndim == 2
        np.testing.assert_array_equal(out, grey)


# ---------------------------------------------------------------------------
# apply_clahe
# ---------------------------------------------------------------------------

class TestApplyClahe:
    def test_output_same_shape(self):
        grey = make_grey_image()
        out = apply_clahe(grey)
        assert out.shape == grey.shape

    def test_output_is_uint8(self):
        grey = make_grey_image()
        out = apply_clahe(grey)
        assert out.dtype == np.uint8


# ---------------------------------------------------------------------------
# estimate_skew_angle
# ---------------------------------------------------------------------------

class TestEstimateSkewAngle:
    def test_level_image_gives_near_zero_angle(self):
        img = make_text_like_image()
        angle = estimate_skew_angle(img)
        assert abs(angle) < 1.5  # within 1.5° of level

    def test_rotated_image_detected(self):
        img = make_text_like_image()
        rotated = deskew(img, -3.0)  # introduce a 3° skew
        angle = estimate_skew_angle(rotated, search_range=10.0, step=0.5)
        # Should detect a correction angle near +3°
        assert abs(angle - 3.0) < 2.0

    def test_uniform_image_returns_float(self):
        img = make_grey_image()
        angle = estimate_skew_angle(img)
        assert isinstance(angle, float)


# ---------------------------------------------------------------------------
# deskew
# ---------------------------------------------------------------------------

class TestDeskew:
    def test_zero_angle_returns_input_unchanged(self):
        grey = make_grey_image()
        out = deskew(grey, 0.0)
        np.testing.assert_array_equal(out, grey)

    def test_tiny_angle_returns_input_unchanged(self):
        grey = make_grey_image()
        out = deskew(grey, 0.05)
        np.testing.assert_array_equal(out, grey)

    def test_output_same_shape(self):
        grey = make_text_like_image()
        out = deskew(grey, 2.5)
        assert out.shape == grey.shape


# ---------------------------------------------------------------------------
# crop_to_content
# ---------------------------------------------------------------------------

class TestCropToContent:
    def test_output_smaller_than_or_equal_to_input(self):
        grey = make_text_like_image()
        out = crop_to_content(grey)
        assert out.shape[0] <= grey.shape[0]
        assert out.shape[1] <= grey.shape[1]

    def test_output_non_empty(self):
        grey = make_text_like_image()
        out = crop_to_content(grey)
        assert out.size > 0

    def test_uniform_white_image_returns_something(self):
        # A fully white image has no dark content; should return trimmed version
        grey = np.full((200, 300), 255, dtype=np.uint8)
        out = crop_to_content(grey)
        assert out.size > 0


# ---------------------------------------------------------------------------
# preprocess_image (integration, using tmp_path)
# ---------------------------------------------------------------------------

class TestPreprocessImage:
    def _write_synthetic_raw(self, path: Path) -> None:
        img = make_text_like_image(h=400, w=600)
        bgr = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        cv2.imwrite(str(path), bgr)

    def test_output_file_created(self, tmp_path):
        raw = tmp_path / "m1.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m1.jpg"
        preprocess_image(raw, out)
        assert out.exists()
        assert out.stat().st_size > 0

    def test_output_filename_preserves_membrane_ref(self, tmp_path):
        raw = tmp_path / "m3.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m3.jpg"
        preprocess_image(raw, out)
        assert out.name == "m3.jpg"

    def test_idempotent_skip(self, tmp_path):
        raw = tmp_path / "m1.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m1.jpg"

        result1 = preprocess_image(raw, out)
        assert not result1.get("skipped")

        result2 = preprocess_image(raw, out)
        assert result2.get("skipped") is True

    def test_force_reruns(self, tmp_path):
        raw = tmp_path / "m1.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m1.jpg"

        preprocess_image(raw, out)
        mtime1 = out.stat().st_mtime

        import time; time.sleep(0.05)
        result = preprocess_image(raw, out, force=True)
        assert not result.get("skipped")

    def test_manifest_record_contains_skew_angle(self, tmp_path):
        raw = tmp_path / "m1.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m1.jpg"
        record = preprocess_image(raw, out)
        assert "skew_angle_deg" in record

    def test_output_is_plausibly_sized(self, tmp_path):
        raw = tmp_path / "m1.jpg"
        self._write_synthetic_raw(raw)
        out = tmp_path / "clean" / "m1.jpg"
        record = preprocess_image(raw, out)
        h, w = record["output_shape_hw"]
        assert h > 50
        assert w > 50
