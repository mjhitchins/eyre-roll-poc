# CLAUDE.md

Operating instructions for Claude Code working on this repository. Read this
first, every session. The full rationale and research context live in
`SPEC.md`; this file is the short, standing brief.

## What this project is

A free, reproducible pipeline that takes manuscript images of a 13th-century
English eyre roll (from the AALT image archive), produces a rough Latin
transcription using a multimodal model, **scores that transcription against a
public-domain printed edition to get a real error rate**, then extracts
structured case-level metrics to CSV for historical analysis.

This is a methods proof-of-concept for a part-time PhD application (medieval
history / digital humanities, University of Bristol). The deliverable that
matters most is **an honest, reported transcription error rate on genuine 1221
court hand**, plus a working structuring step. A high error rate is an
acceptable and publishable finding — do not hide it, tune it away silently, or
fabricate better numbers.

## Non-negotiable principles

1. **No paid tools, licences, or subscriptions.** Everything must run with
   free/open libraries and freely available sources. If a step seems to need a
   paid service, stop and flag it rather than introducing it.
2. **Validation is the point, not an afterthought.** Every transcription run is
   scored against ground truth (Maitland 1884). Never report transcription
   quality by impression; always compute CER/WER.
3. **Provenance is sacred.** Every image, every transcribed line, every CSV row
   must be traceable back to a specific membrane/page reference. The membrane
   reference is the citation anchor and must survive every processing step,
   usually in the filename and in a column.
4. **The model is not ground truth.** Treat all model output (transcription and
   structuring) as a fallible instrument whose error must be measured and
   reported. This framing is the intellectual core of the project.
5. **Reproducibility.** Anyone should be able to clone the repo, run the
   documented commands, and reproduce the numbers. Pin dependencies. Script
   everything; no manual undocumented steps.
6. **Historian-legible.** Code and outputs are read by historians, not just
   engineers. Comment the medieval-specific logic (abbreviations, Latin forms,
   amercement vocabulary). Prefer clarity over cleverness.

## Ground truth and sources

- **Gold-standard text:** F. W. Maitland, *Pleas of the Crown for the County of
  Gloucester ... 1221* (Macmillan, 1884). Public domain. Latin transcription of
  the 1221 Gloucestershire crown pleas.
  - Internet Archive identifier: `crowncountyplea00glouuoft`
  - HathiTrust backup: `hvd.32044018946087`
- **Manuscript images:** AALT (Anglo-American Legal Tradition, University of
  Houston). The 1221 Gloucestershire eyre crown pleas sit in the TNA **JUST 1**
  series. URLs are patterned by class / regnal year / membrane.
- **Later editions (reference only, may be paywalled, NOT required):** Stenton,
  Selden Society vol. 59 (1940), Latin + facing English. Watson (1902), Bristol
  / Swineshead hundred pleas — relevant to the Bristol-centric framing later.

**The linchpin to confirm before trusting any score:** that a given AALT
membrane image and a given Maitland page transcribe the *same* physical text.
Maitland's page/membrane concordance must be established and recorded in
`data/concordance.csv` before alignment scoring is meaningful. The full
procedure and the three required verifications live in `CONCORDANCE.md`; follow
it, and never compute a reported score from a row whose `verified` is not `yes`.

## Tech stack

- Python 3.11+. Use a virtual environment (`.venv`). Pin everything in
  `requirements.txt`.
- Core libs: `requests` (harvest), `Pillow` + `opencv-python` (preprocess),
  `pandas` (collate), `jiwer` or a hand-rolled Levenshtein (scoring),
  `pytest` (tests).
- Multimodal transcription via the model the user has access to; the call must
  sit behind a thin adapter (`src/transcribe/model_client.py`) so the model
  backend can be swapped without touching the rest of the pipeline. Never
  hard-code credentials; read from environment variables.

## Repository layout

```
.
├── CLAUDE.md                 # this file
├── SPEC.md                   # full specification and research context
├── requirements.txt
├── README.md                 # quickstart for a human
├── data/
│   ├── concordance.csv       # membrane <-> Maitland page mapping (hand-built)
│   ├── ground_truth/         # extracted Maitland Latin, one file per page
│   ├── images_raw/           # harvested AALT JPEGs (gitignored, large)
│   └── images_clean/         # preprocessed images (gitignored)
├── output/
│   ├── transcripts/          # model transcriptions, one per membrane
│   ├── scores/               # CER/WER reports
│   └── metrics/              # final structured CSVs
├── docs/                     # generated static site for GitHub Pages
│   └── .nojekyll             # serve files as-is, no Jekyll
├── src/
│   ├── harvest/              # step 1: download AALT images
│   ├── preprocess/           # step 2: clean images
│   ├── transcribe/           # step 3: image -> Latin text
│   ├── score/                # step 4: transcript vs ground truth
│   ├── structure/            # step 5: text -> structured fields
│   ├── collate/              # step 6: CSV -> metrics
│   └── publish/              # step 7: outputs -> static site
└── tests/
```

## Workflow rules for Claude Code

- **Work one pipeline stage at a time.** Each of the six `src/` stages is an
  independent, testable unit with a clear input/output contract (see SPEC.md
  §Pipeline). Do not start a stage until the previous stage's output exists and
  has been eyeballed.
- **Build the scoring stage (4) early**, even before transcription is good — a
  scorer that runs on a tiny hand-made sample proves the measurement loop works.
- **Write the test alongside the code**, not after. At minimum: harvest URL
  construction, preprocess idempotence, scorer correctness on known string
  pairs, structurer parsing on a fixed sample transcript.
- **Keep large binaries out of git.** Images and scans are gitignored; the repo
  holds code, the concordance, ground-truth text, and result CSVs/reports only.

## Version control (git)

- This project is under git. Commit in small, coherent units — one pipeline
  stage, fix, or document per commit — with clear messages (imperative mood,
  e.g. "Add CER/WER scorer", "Fix amercement parsing for marks").
- **Always confirm with the user before committing.** Stage the changes, show
  what will be committed (`git status` and a `git diff --stat`, or the proposed
  message), and wait for explicit approval. Never commit automatically as part
  of finishing a task.
- **Never** `git push`, create or change branches, force-push, amend already-
  shared history, or alter remotes without explicit instruction each time.
- Confirm `.gitignore` excludes `data/images_raw/`, `data/images_clean/`, the
  `.venv/`, environment files, and any credentials **before** the first commit.
  Never commit images, scans, secrets, or API keys.
- If a commit would include something large or sensitive, stop and flag it
  rather than committing.
- **Latin/abbreviation logic gets a comment and, where reasonable, a test.**
  Expansion rules (e.g. expanding common scribal abbreviations) live in one
  documented module, not scattered.
- **When unsure about a historical or archival fact, stop and ask** rather than
  inventing a plausible-sounding answer. Wrong provenance is worse than no
  provenance.
- **Every run writes a small run-manifest** (timestamp, model identifier,
  source image refs, parameters) next to its output so results are reproducible
  and citable.

## Definition of done for the pilot

A single command (or short documented sequence) that, for at least one
confirmed membrane:
1. fetches the AALT image,
2. preprocesses it,
3. transcribes it,
4. reports a CER and WER against the matched Maitland page,
5. emits a structured CSV of the cases on that membrane,

and a short `output/scores/REPORT.md` stating the error rate, what failed, and
the main abbreviation/hand features that caused errors. That report is the
artefact the PhD application draws on. Stage 7 then renders the derived metrics
and headline error rate as a lightweight public proof-of-concept page (`docs/`),
hosted free on GitHub Pages — see `SPEC.md` §Stage 7 and Appendix A. The page is
deliberately minimal and temporary (university infrastructure is the eventual
home); it shows derived metrics, not manuscript images.
