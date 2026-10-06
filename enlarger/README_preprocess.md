# preprocess_rolls.py

Prepares AALT eyre-roll images (JUST 1) for multimodal transcription. Free and open source only, using OpenCV and NumPy.

## Install

```bash
pip install opencv-python-headless numpy requests
```

## Usage

```bash
python preprocess_rolls.py <src> <dst> [options]
```

`src` is a single image, a folder of images (`.jpg`, `.png` or `.tif`), **or an AALT URL** — either a direct image URL or an AALT `.htm` viewer page (the `<img>` tag is resolved automatically). A URL is downloaded and cached under `<dst>/_downloaded/` (a repeat run reuses the cached copy rather than re-fetching). Output goes to `dst`. The script never modifies the original images, and the treated result opens automatically when done (`--no-open` to suppress).

```bash
# Grab a membrane image straight from AALT and see the treated version
python preprocess_rolls.py http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271/aJUST1no271fronts/IMG_3878.htm enlarged/
```

```bash
# Defaults
python preprocess_rolls.py data/raw/ data/processed/

# Colour-preserving, with 4 overlapping strips per membrane
python preprocess_rolls.py data/raw/ data/processed/ --keep-colour --tiles 4

# Heavier treatment for faded membranes
python preprocess_rolls.py data/raw/ data/processed/ --scale 2 --clahe 3.5 --denoise 10
```

## Pipeline

| Step | Default | Option | Off |
|---|---|---|---|
| Lanczos upscale | 1.5x | `--scale` | `--scale 1` |
| Background flattening (median-blur divide) | on | `--bg-frac 0.03` | `--no-flatten` |
| Non-local-means denoise | 7 | `--denoise` | `--denoise 0` |
| CLAHE local contrast | 2.5 | `--clahe`, `--clahe-grid 8` | `--clahe 0` |
| Unsharp mask | 0.8 | `--sharpen`, `--sharpen-radius 2.0` | `--sharpen 0` |
| Sauvola binarisation | off | `--binarise` | — |
| Colour preservation (LAB L-channel) | off | `--keep-colour` | — |
| Horizontal strip tiling | off | `--tiles N`, `--overlap 0.08` | — |

Other options: `--format png|jpg|tif` (default `png`).

## Outputs

- `<stem>.png`: the processed full image.
- `<stem>_tNN.png`: overlapping strips, written only when `--tiles` is used.
- `preprocess_params.json`: the settings used for the run. Keep this file with the outputs so error rates can be traced back to the settings that produced them.

## Notes

- Upscaling adds no real detail, and models downscale large inputs anyway. Tiling usually helps transcription more than a higher `--scale`.
- Don't binarise by default. It tends to destroy faint abbreviation marks and superscripts.
- Choose settings empirically. Run a few concordance-matched images, raw and with 2–3 setting combinations, through the scoring stage against Maitland. Then lock in the best-scoring settings in `SPEC.md`.
- Real-ESRGAN is open source but can invent stroke shapes, so keep it out of any scored runs.

## Possible next steps (Claude Code)

- Wire into the pipeline as the preprocessing stage between harvesting and transcription.
- Add a `--compare` option that writes before-and-after side-by-side images.
- Add a settings-sweep mode that writes each combination to its own subfolder for the scoring stage.
- Optional deskew and crop-to-membrane step.
