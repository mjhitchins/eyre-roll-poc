#!/usr/bin/env python3
"""
preprocess_rolls.py — prepare AALT eyre-roll images for transcription.

Free/open-source only: OpenCV + NumPy (pip install opencv-python-headless numpy).

Pipeline (each step optional, all parameters logged to a sidecar JSON so
results are reproducible and can be reported alongside error rates):

  1. Upscale (Lanczos)              — modest, 1.5–2x; more adds no real detail
  2. Background flattening          — divides out parchment staining / uneven light
  3. Denoise (non-local means)      — removes JPEG blockiness and grain
  4. CLAHE local contrast           — lifts faded ink without blowing out the page
  5. Unsharp mask                   — crisps stroke edges
  6. Optional binarisation (Sauvola-style) — usually NOT recommended for LLMs
  7. Optional tiling                — overlapping horizontal strips, so the
                                       transcription model sees full resolution

Originals are never modified; outputs go to a separate folder.

`src` can also be an AALT URL — either a direct image URL or an AALT
".htm" viewer page (the <img> tag is resolved automatically) — in which
case the image is downloaded, cached under <dst>/_downloaded/ (repeat runs
reuse the cached copy rather than re-fetching), and processed the same way
as a local file. The result opens automatically unless --no-open is given.

Usage:
  python preprocess_rolls.py raw/ processed/
  python preprocess_rolls.py raw/ processed/ --scale 2 --clahe 3.0 --tiles 4
  python preprocess_rolls.py raw/IMG_0012.jpg processed/ --keep-colour
  python preprocess_rolls.py http://aalt.law.uh.edu/.../IMG_3878.htm processed/
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

import cv2
import numpy as np
import requests

EXTS = {".jpg", ".jpeg", ".png", ".tif", ".tiff"}

_HTTP_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; eyre-roll-poc-enlarger/0.1; "
        "educational research contact mark.hitchins@myadminmate.com)"
    )
}


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def resolve_image_url(url: str) -> str:
    """If url is an AALT .htm viewer page, resolve it to the actual image URL.

    AALT viewer pages embed several <img> tags — "Backward"/"Forward"
    navigation arrows (absolute URLs under /images/) plus the actual scan,
    which is an "IMG_####.JPG" src relative to the page itself. Taking the
    first <img> tag unconditionally grabs a 75x39 nav arrow, not the scan —
    so this specifically prefers a src matching the page's own IMG_#### filename
    pattern, falling back to "first <img>" only if none is found.
    """
    if not url.lower().endswith((".htm", ".html")):
        return url
    resp = requests.get(url, headers=_HTTP_HEADERS, timeout=30)
    resp.raise_for_status()

    srcs = re.findall(r'<img\s[^>]*\bsrc=["\']([^"\']+)["\']', resp.text, re.IGNORECASE)
    if not srcs:
        raise RuntimeError(f"could not find an <img> tag in {url}")
    scan = next((s for s in srcs if re.search(r'IMG_\d+\.(jpe?g)$', s, re.IGNORECASE)), None)
    src = scan or srcs[0]

    if src.startswith("http"):
        return src
    base_dir = url.rsplit("/", 1)[0]
    return f"{base_dir}/{src.lstrip('/')}"


def download_image(url: str, cache_dir: Path) -> Path:
    """
    Resolve url to an image, download it, and cache it under cache_dir.
    Returns the cached local path, re-downloading only if not already cached.
    """
    img_url = resolve_image_url(url)
    filename = Path(urlsplit(img_url).path).name or "image"
    if not any(filename.lower().endswith(ext) for ext in EXTS):
        filename += ".jpg"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_path = cache_dir / filename

    if cached_path.exists():
        print(f"using cached download: {cached_path}")
        return cached_path

    print(f"downloading {img_url} ...")
    resp = requests.get(img_url, headers=_HTTP_HEADERS, timeout=30)
    resp.raise_for_status()
    cached_path.write_bytes(resp.content)
    print(f"saved -> {cached_path}")
    return cached_path


def open_for_viewing(paths: list[Path]) -> None:
    """Best-effort: open images in the OS default viewer. Never fatal."""
    opener = {"darwin": "open", "linux": "xdg-open"}.get(sys.platform)
    if opener is None:
        print("(--open is not supported on this platform; open the file(s) manually)")
        return
    for path in paths:
        try:
            subprocess.run([opener, str(path)], check=False)
        except OSError as exc:
            print(f"could not open {path}: {exc}")


def flatten_background(gray: np.ndarray, kernel_frac: float) -> np.ndarray:
    """Estimate the parchment background with a large median blur and divide it out."""
    k = max(31, int(min(gray.shape) * kernel_frac) | 1)  # odd kernel
    k = min(k, 255)  # medianBlur limit for 8-bit
    bg = cv2.medianBlur(gray, k)
    flat = cv2.divide(gray, bg, scale=255)
    return flat


def sauvola(gray: np.ndarray, window: int = 41, k: float = 0.2) -> np.ndarray:
    g = gray.astype(np.float32)
    mean = cv2.boxFilter(g, -1, (window, window))
    sqmean = cv2.boxFilter(g * g, -1, (window, window))
    std = np.sqrt(np.maximum(sqmean - mean * mean, 0))
    thresh = mean * (1 + k * (std / 128.0 - 1))
    return np.where(g > thresh, 255, 0).astype(np.uint8)


def process(img: np.ndarray, a) -> np.ndarray:
    if a.scale and a.scale != 1:
        img = cv2.resize(img, None, fx=a.scale, fy=a.scale, interpolation=cv2.INTER_LANCZOS4)

    if a.keep_colour:
        # Work on the L channel only, keep the colour (helps distinguish ink from stains)
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        L, A, B = cv2.split(lab)
    else:
        L = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    if not a.no_flatten:
        L = flatten_background(L, a.bg_frac)
    if a.denoise > 0:
        L = cv2.fastNlMeansDenoising(L, None, h=a.denoise, templateWindowSize=7, searchWindowSize=21)
    if a.clahe > 0:
        clahe = cv2.createCLAHE(clipLimit=a.clahe, tileGridSize=(a.clahe_grid, a.clahe_grid))
        L = clahe.apply(L)
    if a.sharpen > 0:
        blur = cv2.GaussianBlur(L, (0, 0), sigmaX=a.sharpen_radius)
        L = cv2.addWeighted(L, 1 + a.sharpen, blur, -a.sharpen, 0)
    if a.binarise:
        L = sauvola(L)

    if a.keep_colour and not a.binarise:
        return cv2.cvtColor(cv2.merge([L, A, B]), cv2.COLOR_LAB2BGR)
    return L


def tiles(img: np.ndarray, n: int, overlap: float):
    """Split into n horizontal strips with overlap (rolls are tall; lines run across)."""
    h = img.shape[0]
    step = h / n
    pad = int(step * overlap)
    for i in range(n):
        y0 = max(0, int(i * step) - pad)
        y1 = min(h, int((i + 1) * step) + pad)
        yield i + 1, img[y0:y1]


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("src", type=str, help="image file, folder, or AALT URL (image or .htm viewer page)")
    p.add_argument("dst", type=Path, help="output folder")
    p.add_argument("--scale", type=float, default=1.5)
    p.add_argument("--no-flatten", action="store_true")
    p.add_argument("--bg-frac", type=float, default=0.03, help="background kernel as fraction of short side")
    p.add_argument("--denoise", type=float, default=7, help="NLM strength, 0 = off")
    p.add_argument("--clahe", type=float, default=2.5, help="clip limit, 0 = off")
    p.add_argument("--clahe-grid", type=int, default=8)
    p.add_argument("--sharpen", type=float, default=0.8, help="unsharp amount, 0 = off")
    p.add_argument("--sharpen-radius", type=float, default=2.0)
    p.add_argument("--binarise", action="store_true", help="black/white output (test before using)")
    p.add_argument("--keep-colour", action="store_true")
    p.add_argument("--tiles", type=int, default=0, help="also write N overlapping strips")
    p.add_argument("--overlap", type=float, default=0.08)
    p.add_argument("--format", default="png", choices=["png", "jpg", "tif"])
    p.add_argument("--open", action=argparse.BooleanOptionalAction, default=True,
                    help="open the treated output automatically when done (default: on)")
    a = p.parse_args()

    a.dst.mkdir(parents=True, exist_ok=True)

    if is_url(a.src):
        files = [download_image(a.src, a.dst / "_downloaded")]
    else:
        src_path = Path(a.src)
        files = [src_path] if src_path.is_file() else sorted(
            f for f in src_path.iterdir() if f.suffix.lower() in EXTS
        )

    params = {k: (str(v) if isinstance(v, Path) else v) for k, v in vars(a).items()}
    (a.dst / "preprocess_params.json").write_text(json.dumps(params, indent=2))

    written = []
    for f in files:
        img = cv2.imread(str(f), cv2.IMREAD_COLOR)
        if img is None:
            print(f"skip (unreadable): {f.name}")
            continue
        out = process(img, a)
        stem = f.stem
        out_path = a.dst / f"{stem}.{a.format}"
        cv2.imwrite(str(out_path), out)
        written.append(out_path)
        if a.tiles:
            for i, t in tiles(out, a.tiles, a.overlap):
                tile_path = a.dst / f"{stem}_t{i:02d}.{a.format}"
                cv2.imwrite(str(tile_path), t)
                written.append(tile_path)
        print(f"ok: {f.name} -> {out.shape[1]}x{out.shape[0]}")

    if a.open and written:
        open_for_viewing(written)


if __name__ == "__main__":
    main()
