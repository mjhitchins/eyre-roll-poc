# Eyre Roll Transcription & Metrics Pipeline

A free, reproducible pipeline that takes manuscript images of a 13th-century
English eyre roll (from the AALT image archive), produces a Latin transcription
using a multimodal model, **scores that transcription against a public-domain
printed edition to get a real error rate**, then extracts structured case-level
metrics to CSV for historical analysis.

This is a methods proof-of-concept for a PhD application (medieval history /
digital humanities, University of Bristol). The central claim is methodological:
that untuned multimodal transcription can be measured and reported honestly
against a gold-standard text. A high error rate is an acceptable and publishable
finding.

---

## Sources

| Source | Description |
|--------|-------------|
| **AALT** (Anglo-American Legal Tradition) | Manuscript images of TNA JUST 1 assize rolls |
| **Maitland 1884** | *Pleas of the Crown for the County of Gloucester, 1221* — public-domain ground truth |
| Internet Archive: `crowncountyplea00glouuoft` | Maitland scan |

---

## Quick start

```bash
# 1. Clone and create virtual environment
git clone <repo-url>
cd eyre-roll-poc
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Set API credentials (needed for Stage 3 transcription)
export ANTHROPIC_API_KEY=your_key_here

# 3. Run the pipeline for one membrane
# (requires data/concordance.csv to have at least one verified row)
python -m src.harvest.run --membrane m1
python -m src.preprocess.run --membrane m1
python -m src.transcribe.run --membrane m1
python -m src.score.run --membrane m1
python -m src.structure.run --membrane m1

# 4. View results
cat output/scores/REPORT.md
cat output/metrics/cases.csv
```

---

## Pipeline stages

| Stage | Module | In | Out |
|-------|--------|----|-----|
| 1 Harvest | `src/harvest/` | membrane refs | `data/images_raw/` JPEGs |
| 2 Preprocess | `src/preprocess/` | raw JPEGs | `data/images_clean/` |
| 3 Transcribe | `src/transcribe/` | clean images | `output/transcripts/` |
| 4 Score | `src/score/` | transcript + ground truth | `output/scores/` CER/WER |
| 5 Structure | `src/structure/` | transcript | `output/metrics/` CSV |
| 6 Collate | `src/collate/` | structured CSVs | aggregate metrics |
| 7 Publish | `src/publish/` | scores + metrics | `site/index.html` |

---

## Repository layout

```
.
├── CLAUDE.md           # standing operating brief for Claude Code
├── SPEC.md             # full specification and research context
├── CONCORDANCE.md      # how to build and verify the image↔edition mapping
├── README.md           # this file
├── CHANGELOG.md
├── requirements.txt
├── data/
│   ├── concordance.csv         # membrane ↔ Maitland page mapping
│   ├── concordance_sources.md  # evidence for the concordance (manual)
│   ├── ground_truth/           # Maitland Latin, one file per page
│   ├── images_raw/             # harvested JPEGs (gitignored)
│   └── images_clean/           # preprocessed images (gitignored)
├── output/
│   ├── transcripts/            # model transcriptions
│   ├── scores/                 # CER/WER reports
│   └── metrics/                # structured case CSVs
├── site/                       # static site for GitHub Pages
├── src/
│   ├── harvest/
│   ├── preprocess/
│   ├── transcribe/
│   ├── score/
│   ├── structure/
│   ├── collate/
│   └── publish/
└── tests/
```

---

## Development workflow

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov=src

# Run a specific stage's tests
pytest tests/test_score.py
```

Stages are independent and tested in isolation. Build Stage 4 (scorer) first on
toy data to prove the measurement loop before transcription exists.

---

## The concordance

`data/concordance.csv` maps AALT membrane images to Maitland edition pages. A
row with `verified = no` **must never be used to compute a reported score**. See
`CONCORDANCE.md` for the full verification procedure (V1–V3).

---

## Principles

- No paid tools, licences, or subscriptions.
- Validation is the point, not an afterthought. Every transcription run is scored against Maitland.
- Provenance is sacred. Every row is traceable to a specific membrane.
- The model is not ground truth. Model output is measured and caveated.
- Reproducible. Pin dependencies; script everything; write run manifests.
- Historian-legible. Comment the medieval-specific logic.

---

## Contributing / future Claude sessions

Read `CLAUDE.md` first. The full rationale for every architectural decision is
in `SPEC.md`. The concordance verification procedure is in `CONCORDANCE.md`.
Never commit images, never report transcription quality by impression, never
compute a score from an unverified concordance row.
