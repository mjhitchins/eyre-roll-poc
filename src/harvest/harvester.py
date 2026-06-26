"""
Stage 1: Harvest AALT images for JUST 1/271 (1221 Gloucestershire eyre).

URL pattern (user-confirmed, 2026-06-26):
  Fronts: .../aJUST1no271fronts/IMG_{num}.htm  IMG_3855–3909  membranes m1–m55
  Dorses: .../bJUST1no271dorses/IMG_{num}.htm  IMG_3910–3955  membranes m1d–m46d

Image files are expected at the same path with .JPG or .jpg extension.
If both fail, the .htm viewer page is fetched and parsed for an img src.
"""

import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

PIECE = "JUST 1/271"
_BASE = "http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271"
_FRONTS_DIR = "aJUST1no271fronts"
_DORSES_DIR = "bJUST1no271dorses"

# Image number ranges, confirmed by browsing AALT index 2026-06-26
_FRONTS_FIRST = 3855   # IMG_3855 = m1 face
_FRONTS_LAST  = 3909   # IMG_3909 = m55 face
_DORSES_FIRST = 3910   # IMG_3910 = m1 dorse
_DORSES_LAST  = 3955   # IMG_3955 = m46 dorse

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; eyre-roll-poc/0.1; "
        "educational research contact mark.hitchins@myadminmate.com)"
    )
}
_RATE_LIMIT_SECS = 2.0
_MAX_RETRIES = 3
_RETRY_WAIT = 5.0


def membrane_to_img_num(membrane_ref: str) -> int:
    """
    Convert a membrane reference to its AALT image number.

    m1→3855 … m55→3909 (faces)
    m1d→3910 … m46d→3955 (dorses)
    """
    ref = membrane_ref.strip().lower()
    if ref.endswith("d"):
        n = int(ref[1:-1])
        max_d = _DORSES_LAST - _DORSES_FIRST + 1
        if not 1 <= n <= max_d:
            raise ValueError(f"Dorse number {n} out of range 1–{max_d}")
        return _DORSES_FIRST + n - 1
    else:
        n = int(ref[1:])
        max_f = _FRONTS_LAST - _FRONTS_FIRST + 1
        if not 1 <= n <= max_f:
            raise ValueError(f"Face number {n} out of range 1–{max_f}")
        return _FRONTS_FIRST + n - 1


def img_page_url(membrane_ref: str) -> str:
    """AALT .htm viewer page URL for a membrane."""
    num = membrane_to_img_num(membrane_ref)
    folder = _DORSES_DIR if membrane_ref.strip().lower().endswith("d") else _FRONTS_DIR
    return f"{_BASE}/{folder}/IMG_{num}.htm"


def img_file_url(membrane_ref: str, ext: str = "JPG") -> str:
    """Direct image URL (same path as .htm but with image extension)."""
    return img_page_url(membrane_ref).replace(".htm", f".{ext}")


def _get(url: str, session: requests.Session, stream: bool = False) -> requests.Response:
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = session.get(url, headers=_HEADERS, timeout=30, stream=stream)
            resp.raise_for_status()
            return resp
        except requests.RequestException as exc:
            if attempt == _MAX_RETRIES:
                raise
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, _MAX_RETRIES, url, exc)
            time.sleep(_RETRY_WAIT)
    raise RuntimeError("unreachable")


def _img_url_from_htm(html: str, page_url: str) -> Optional[str]:
    """Extract first img src from an AALT viewer page and resolve it to absolute."""
    m = re.search(r'<img\s[^>]*\bsrc=["\']([^"\']+)["\']', html, re.IGNORECASE)
    if not m:
        return None
    src = m.group(1)
    if src.startswith("http"):
        return src
    base_dir = page_url.rsplit("/", 1)[0]
    return f"{base_dir}/{src.lstrip('/')}"


def download_membrane_image(
    membrane_ref: str,
    output_dir: Path,
    session: Optional[requests.Session] = None,
    rate_limit: float = _RATE_LIMIT_SECS,
) -> Path:
    """
    Download the AALT JPEG for one membrane to output_dir/{membrane_ref}.jpg.

    Skips the download if the file already exists (idempotent).
    Returns the path to the saved file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{membrane_ref}.jpg"

    if out_path.exists():
        logger.info("Already downloaded: %s", out_path)
        return out_path

    own_session = session is None
    if own_session:
        session = requests.Session()

    try:
        # Try direct JPG/jpg URLs before falling back to .htm parsing
        for ext in ("JPG", "jpg"):
            url = img_file_url(membrane_ref, ext)
            try:
                logger.info("Trying %s", url)
                time.sleep(rate_limit)
                resp = _get(url, session, stream=True)
                data = resp.content
                if data[:3] == b"\xff\xd8\xff":  # JPEG magic bytes
                    out_path.write_bytes(data)
                    logger.info("Saved %s (%d bytes) → %s", url, len(data), out_path)
                    return out_path
            except requests.RequestException:
                continue

        # Fall back to parsing the .htm viewer page
        htm_url = img_page_url(membrane_ref)
        logger.info("Fetching viewer page: %s", htm_url)
        time.sleep(rate_limit)
        page = _get(htm_url, session)
        img_url = _img_url_from_htm(page.text, htm_url)
        if img_url is None:
            raise RuntimeError(f"Could not locate image URL in {htm_url}")

        logger.info("Found image: %s", img_url)
        time.sleep(rate_limit)
        resp = _get(img_url, session, stream=True)
        data = resp.content
        out_path.write_bytes(data)
        logger.info("Saved %s (%d bytes) → %s", img_url, len(data), out_path)
        return out_path

    finally:
        if own_session:
            session.close()


def write_manifest(
    membrane_refs: list[str],
    downloaded: list[Path],
    output_dir: Path,
) -> Path:
    """Write a JSON run manifest to output_dir."""
    manifest = {
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "piece": PIECE,
        "aalt_base_url": _BASE,
        "membranes": [
            {
                "membrane_ref": ref,
                "page_url": img_page_url(ref),
                "saved_to": str(p),
            }
            for ref, p in zip(membrane_refs, downloaded)
        ],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = output_dir / f"harvest_manifest_{ts}.json"
    path.write_text(json.dumps(manifest, indent=2))
    logger.info("Manifest written: %s", path)
    return path
