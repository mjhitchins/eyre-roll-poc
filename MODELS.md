# MODELS.md — Kraken HTR Model Download

Stage 3 transcription uses [Kraken](https://kraken.re), a free open-source
HTR engine. Kraken requires a separate `.mlmodel` file that is **not** stored
in this repository (too large for git; not our copyright to redistribute).

---

## Recommended model: CATMuS Medieval

**CATMuS Medieval** is the best freely available Kraken model for 13th-century
Latin manuscripts. It was trained on thousands of lines from medieval Western
European manuscripts (9th–16th century) covering Latin, Old French, and
related scripts, drawn from CREMMA Medieval, GalliCorpora, Eutyches, Caroline
Minuscule datasets, and others.

It is not trained specifically on English court hand, so expect errors —
particularly on minims, common abbreviations (q̃, p̄, ā), and the compressed
formulaic Latin of plea rolls. That imperfection is what the CER/WER scorer
(Stage 4) measures and reports.

### Download via Kraken CLI (recommended)

```bash
source .venv/bin/activate
mkdir -p models
# List DOI for CATMuS Medieval 1.5.0
kraken get 10.5281/zenodo.12743230
# Kraken downloads to ~/.kraken/ by default; copy to models/
cp ~/.kraken/en_best.mlmodel models/catmus-medieval.mlmodel  # adjust filename as needed
```

Or browse the full Zenodo record directly:
`https://zenodo.org/records/12743230`

Download the `.mlmodel` file and save it to `models/` in this repo root.
The `models/` directory is gitignored (see `.gitignore`).

### Alternative: use kraken's get command with DOI

```bash
kraken get 10.5281/zenodo.12743230
```

This downloads to `~/.kraken/` on your system. Note the exact filename it
prints, then pass that path to the `--model` flag.

---

## Running transcription

Once the model is in `models/`:

```bash
source .venv/bin/activate

# Transcribe membrane m1 (must have run harvest + preprocess first)
python -m src.transcribe.run \
    --membrane m1 \
    --model models/catmus-medieval.mlmodel
```

Output goes to `output/transcripts/m1.txt` plus a manifest JSON.

---

## Other available models

Run `kraken list` (with the venv active) to see all models in Kraken's
registry. Relevant keywords to look for: `medieval`, `latin`, `handwritten`.

If a model trained specifically on English 13th-century Chancery/Exchequer
hand becomes available (e.g., through the Mappa Mundi or PDPF projects),
that would supersede CATMuS Medieval for this project. Check HTR-United:
`https://htr-united.github.io`

---

## Why models are not committed to git

- `.mlmodel` files are typically 20–200 MB — too large for a git repo.
- They carry their own licences (usually CC-BY or CC-BY-SA) and must be
  attributed, not silently bundled.
- Pinning the Zenodo DOI in this file is the reproducible reference;
  anyone cloning the repo can download the exact same model.
