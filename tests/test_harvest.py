"""
Tests for Stage 1: AALT image harvester.

Covers URL construction and membrane-ref ↔ image-number mapping.
Network calls are not made in tests; download logic is tested with a mock.
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from src.harvest.harvester import (
    membrane_to_img_num,
    img_page_url,
    img_file_url,
    _FRONTS_FIRST,
    _FRONTS_LAST,
    _DORSES_FIRST,
    _DORSES_LAST,
)


# ---------------------------------------------------------------------------
# membrane_to_img_num — round-trip tests
# ---------------------------------------------------------------------------

class TestMembraneToImgNum:
    def test_m1_is_first_front(self):
        assert membrane_to_img_num("m1") == _FRONTS_FIRST

    def test_m55_is_last_front(self):
        n_fronts = _FRONTS_LAST - _FRONTS_FIRST + 1
        assert membrane_to_img_num(f"m{n_fronts}") == _FRONTS_LAST

    def test_m1d_is_first_dorse(self):
        assert membrane_to_img_num("m1d") == _DORSES_FIRST

    def test_last_dorse(self):
        n_dorses = _DORSES_LAST - _DORSES_FIRST + 1
        assert membrane_to_img_num(f"m{n_dorses}d") == _DORSES_LAST

    def test_sequential_fronts(self):
        assert membrane_to_img_num("m2") == _FRONTS_FIRST + 1
        assert membrane_to_img_num("m3") == _FRONTS_FIRST + 2

    def test_sequential_dorses(self):
        assert membrane_to_img_num("m2d") == _DORSES_FIRST + 1

    def test_case_insensitive(self):
        assert membrane_to_img_num("M1") == membrane_to_img_num("m1")
        assert membrane_to_img_num("M1D") == membrane_to_img_num("m1d")

    def test_out_of_range_front_raises(self):
        with pytest.raises(ValueError):
            membrane_to_img_num("m999")

    def test_out_of_range_dorse_raises(self):
        with pytest.raises(ValueError):
            membrane_to_img_num("m999d")


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------

class TestUrlConstruction:
    def test_m1_page_url(self):
        url = img_page_url("m1")
        assert "aJUST1no271fronts" in url
        assert f"IMG_{_FRONTS_FIRST}.htm" in url
        assert url.startswith("http://aalt.law.uh.edu")

    def test_m1d_page_url(self):
        url = img_page_url("m1d")
        assert "bJUST1no271dorses" in url
        assert f"IMG_{_DORSES_FIRST}.htm" in url

    def test_img_file_url_default_extension(self):
        url = img_file_url("m1")
        assert url.endswith(".JPG")
        assert ".htm" not in url

    def test_img_file_url_lowercase_extension(self):
        url = img_file_url("m1", ext="jpg")
        assert url.endswith(".jpg")

    def test_fronts_and_dorses_use_different_folders(self):
        front_url = img_page_url("m1")
        dorse_url = img_page_url("m1d")
        assert "fronts" in front_url
        assert "dorses" in dorse_url
        assert front_url != dorse_url

    def test_concordance_m1_url_matches(self):
        # Confirm the URL matches what is recorded in concordance.csv for m1
        expected = (
            "http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271"
            "/aJUST1no271fronts/IMG_3855.htm"
        )
        assert img_page_url("m1") == expected

    def test_concordance_m1d_url_matches(self):
        expected = (
            "http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271"
            "/bJUST1no271dorses/IMG_3910.htm"
        )
        assert img_page_url("m1d") == expected
