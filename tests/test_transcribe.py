"""
Tests for Stage 3: Kraken HTR transcription adapter.

All tests are offline — no model file is required.  Kraken's internals are
patched at the module boundary so that model_client.py is exercised without
needing a real .mlmodel download.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from src.transcribe.transcriber import transcribe_membrane
from src.transcribe.model_client import transcribe_image


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_LINES = [
    "Rogerus de Clifford in misericordia pro falso clamore",
    "Willelmus filius Hugonis ponit se super patriam",
    "m",
]

SAMPLE_TRANSCRIPT = "\n".join(f"{i + 1}  {line}" for i, line in enumerate(SAMPLE_LINES))


def _make_mock_records(lines=None):
    """Return a list of mock Kraken ocr_record objects."""
    if lines is None:
        lines = SAMPLE_LINES
    records = []
    for text in lines:
        r = MagicMock()
        r.prediction = text
        records.append(r)
    return records


def _write_dummy_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("L", (10, 10), color=200)
    img.save(str(path), format="JPEG")


def _write_dummy_model(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-model-data")


def _patch_kraken(lines=None):
    """Patch all Kraken internals; return a context-manager-style patcher dict."""
    mock_records = _make_mock_records(lines)
    mock_net = MagicMock()
    mock_bim = MagicMock(spec=Image.Image)

    p_load = patch("src.transcribe.model_client.models.load_any", return_value=mock_net)
    p_nlbin = patch("src.transcribe.model_client.binarization.nlbin", return_value=mock_bim)
    p_seg = patch("src.transcribe.model_client.pageseg.segment", return_value=MagicMock())
    p_rpred = patch("src.transcribe.model_client.rpred.rpred", return_value=iter(mock_records))
    return p_load, p_nlbin, p_seg, p_rpred


# ---------------------------------------------------------------------------
# transcribe_image (model_client)
# ---------------------------------------------------------------------------

class TestTranscribeImage:
    def test_returns_numbered_transcript(self, tmp_path):
        img = tmp_path / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)

        patchers = _patch_kraken()
        for p in patchers:
            p.start()
        try:
            result = transcribe_image(img, model)
        finally:
            for p in patchers:
                p.stop()

        assert result["transcript"] == SAMPLE_TRANSCRIPT
        assert result["stop_reason"] == "end_turn"

    def test_line_numbers_are_sequential(self, tmp_path):
        img = tmp_path / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)

        patchers = _patch_kraken(["first", "second", "third"])
        for p in patchers:
            p.start()
        try:
            result = transcribe_image(img, model)
        finally:
            for p in patchers:
                p.stop()

        lines = result["transcript"].splitlines()
        assert lines[0].startswith("1  ")
        assert lines[1].startswith("2  ")
        assert lines[2].startswith("3  ")

    def test_missing_model_raises(self, tmp_path):
        img = tmp_path / "m1.jpg"
        _write_dummy_image(img)
        missing_model = tmp_path / "nonexistent.mlmodel"

        with pytest.raises(FileNotFoundError, match="Kraken model not found"):
            transcribe_image(img, missing_model)

    def test_usage_is_zeroed(self, tmp_path):
        img = tmp_path / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)

        patchers = _patch_kraken()
        for p in patchers:
            p.start()
        try:
            result = transcribe_image(img, model)
        finally:
            for p in patchers:
                p.stop()

        assert result["usage"]["input_tokens"] == 0
        assert result["usage"]["output_tokens"] == 0

    def test_model_path_recorded(self, tmp_path):
        img = tmp_path / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)

        patchers = _patch_kraken()
        for p in patchers:
            p.start()
        try:
            result = transcribe_image(img, model)
        finally:
            for p in patchers:
                p.stop()

        assert "model.mlmodel" in result["model"]


# ---------------------------------------------------------------------------
# transcribe_membrane (transcriber)
# ---------------------------------------------------------------------------

class TestTranscribeMembrane:
    def _run(self, membrane_ref, img, model, out_dir, force=False, lines=None):
        patchers = _patch_kraken(lines)
        for p in patchers:
            p.start()
        try:
            return transcribe_membrane(
                membrane_ref=membrane_ref,
                clean_image_path=img,
                output_dir=out_dir,
                model_path=model,
                force=force,
            )
        finally:
            for p in patchers:
                p.stop()

    def test_transcript_file_created(self, tmp_path):
        img = tmp_path / "images_clean" / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)
        out_dir = tmp_path / "transcripts"

        result = self._run("m1", img, model, out_dir)

        assert not result.get("skipped")
        transcript_path = Path(result["transcript_path"])
        assert transcript_path.exists()
        assert transcript_path.read_text() == SAMPLE_TRANSCRIPT

    def test_manifest_written(self, tmp_path):
        img = tmp_path / "images_clean" / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)
        out_dir = tmp_path / "transcripts"

        result = self._run("m1", img, model, out_dir)

        manifest_path = Path(result["manifest_path"])
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text())
        assert manifest["membrane_ref"] == "m1"
        assert "timestamp_utc" in manifest
        assert "model" in manifest

    def test_idempotent_skip(self, tmp_path):
        img = tmp_path / "images_clean" / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)
        out_dir = tmp_path / "transcripts"

        self._run("m1", img, model, out_dir)
        result2 = self._run("m1", img, model, out_dir)

        assert result2.get("skipped") is True

    def test_force_reruns(self, tmp_path):
        img = tmp_path / "images_clean" / "m1.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)
        out_dir = tmp_path / "transcripts"

        self._run("m1", img, model, out_dir)
        result2 = self._run("m1", img, model, out_dir, force=True)

        assert not result2.get("skipped")

    def test_missing_image_raises(self, tmp_path):
        model = tmp_path / "model.mlmodel"
        _write_dummy_model(model)
        missing_img = tmp_path / "images_clean" / "m99.jpg"
        out_dir = tmp_path / "transcripts"

        with pytest.raises(FileNotFoundError, match="Clean image not found"):
            transcribe_membrane("m99", missing_img, out_dir, model)

    def test_membrane_ref_preserved_in_manifest(self, tmp_path):
        img = tmp_path / "images_clean" / "m1d.jpg"
        model = tmp_path / "model.mlmodel"
        _write_dummy_image(img)
        _write_dummy_model(model)
        out_dir = tmp_path / "transcripts"

        result = self._run("m1d", img, model, out_dir)

        manifest = json.loads(Path(result["manifest_path"]).read_text())
        assert manifest["membrane_ref"] == "m1d"
