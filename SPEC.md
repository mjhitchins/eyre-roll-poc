# SPEC.md — Eyre Roll Transcription & Metrics Pipeline

Full specification and research context. Pair with `CLAUDE.md` (the standing
operating brief). This document explains *why* each decision exists so the
pipeline can be defended in a PhD application and viva, not just run.

---

## 1. Research context

### 1.1 The thesis this serves

A part-time PhD in medieval history with a digital-humanities methodology,
targeted at the University of Bristol. The substantive historical question is
whether the administration of royal justice in 13th-century England represented
**bottom-up community demand for order** or **top-down revenue-raising and
control** — bounded by time, place, and evidence set. State formation (how
ordinary people came to buy into shared institutions and law) is the deeper
intellectual engine, not necessarily the foregrounded question.

The eyre rolls are ideal because they are a **homogeneous, high-volume, serial
corpus**: the same kinds of entry (presentment, plea, verdict, amercement,
deodand) recur in volume, which is exactly what computational collation needs,
and because the individual cases — "Richard killed John after the ale" — are
simultaneously the quantitative data *and* the social-history texture.

### 1.2 What this repository proves

This is the **technical proof-of-concept** for the application's methods
section. It must demonstrate, with honest numbers, that:

1. AALT manuscript images can be turned into usable Latin transcription by a
   free multimodal model;
2. that transcription's accuracy can be **measured against a public-domain
   printed edition** and reported as a real error rate;
3. the transcribed text can be **structured into case-level metrics** suitable
   for quantitative historical analysis.

The honest reporting of where the method fails is itself a contribution. An
untuned multimodal model on heavily abbreviated 1221 court hand may produce a
high error rate; documenting that, and the validation regime around it, is the
scholarly point. Do not overstate the method.

### 1.3 Geographic focus

Bristol-centric: Gloucestershire, with Somerset and Devon of secondary
interest. The 1221 Gloucestershire eyre is chosen for the pilot specifically
because it has the best free ground-truth coverage (see §2).

---

## 2. Sources and ground truth

### 2.1 Gold-standard transcription (free, public domain)

**F. W. Maitland (ed.), _Pleas of the Crown for the County of Gloucester before
the Abbot of Reading and his fellows Justices Itinerant ... 1221_ (Macmillan,
1884).** Full Latin transcription of the 1221 Gloucestershire crown pleas.
Public domain.

- Internet Archive: `crowncountyplea00glouuoft`
  (https://archive.org/details/crowncountyplea00glouuoft)
- HathiTrust backup: `hvd.32044018946087`

This is the project's ground truth. It is what model transcriptions are scored
against. It was chosen over the Selden Society edition (Stenton, vol. 59, 1940)
precisely because Maitland is out of copyright and freely downloadable, keeping
the project within the no-paid-sources rule.

### 2.2 Manuscript images

**AALT — Anglo-American Legal Tradition** (University of Houston Law Center).
Photographs of the membranes. The 1221 Gloucestershire eyre crown pleas are in
the TNA **JUST 1** assize-roll series. AALT image URLs follow a predictable
pattern by record class, regnal year, and membrane number, which makes scripted
harvesting possible.

Practical notes:
- Images are photographs of parchment, often shot at a slight angle with
  membrane edges and background visible. Cropping and deskewing materially help.
- The hand is an early-13th-century documentary court hand with heavy scribal
  abbreviation. This is the hard case for any HTR/OCR.
- Keep the membrane reference in every filename; it is the citation anchor.

### 2.3 Reference-only sources (not required, may be paywalled)

- Stenton, *Rolls of the Justices in Eyre ... Gloucestershire, Warwickshire and
  Shropshire, 1221, 1222*, Selden Society vol. 59 (1940) — Latin + facing
  English translation. Useful later for translation work; not needed for the
  technical pilot.
- Watson (ed.), *Pleas of the Crown for the Hundred of Swineshead and the
  Township of Bristol* (1902) — directly relevant to the Bristol focus in a
  later phase.

### 2.4 The concordance problem (do this first)

Scoring is only meaningful if the AALT image and the Maitland page describe the
**same physical text**. Before any score is trusted, build
`data/concordance.csv` mapping AALT membrane references to Maitland page/section
numbers. This is partly manual scholarly work; the pipeline depends on it but
cannot fully automate it. Record uncertainty explicitly.

The mechanism: Maitland prints **membrane numbers in the margin** ("m. 1",
"m. 1d") marking where each membrane begins; AALT names its images per membrane
face. The concordance maps the two. Three verifications must pass first —
(V1) confirm the correct TNA JUST 1 piece against Maitland's preface and TNA
Discovery, noting that Maitland covers the **crown pleas only**, not necessarily
the whole roll (the full eyre is Stenton, Selden Society vol. 59); (V2) confirm
that piece is present in AALT and establish its image-numbering scheme;
(V3) spot-check the alignment on one distinctive plea by eye. The full procedure,
the `concordance.csv` schema, and the companion `concordance_sources.md`
evidence file are specified in **`CONCORDANCE.md`** (repo root). A row whose
`verified` is not `yes` must never be used to compute a reported score.

---

## 3. Pipeline

Six independent, testable stages. Each has a strict input/output contract so
stages can be built and validated one at a time.

### Stage 1 — Harvest (`src/harvest/`)
- **In:** a list of AALT membrane references (class, regnal year, membrane).
- **Out:** JPEGs in `data/images_raw/`, named with their membrane reference.
- Construct URLs from the AALT pattern; download politely (rate-limit, retry,
  cache; never re-download an existing file). Write a run-manifest listing every
  URL fetched and its membrane ref.
- **Tests:** URL construction from references; filename ↔ reference round-trip.

### Stage 2 — Preprocess (`src/preprocess/`)
- **In:** raw JPEGs.
- **Out:** cleaned images in `data/images_clean/`.
- Greyscale → contrast normalisation → deskew → crop to text block. Use Pillow +
  OpenCV. Operations must be **idempotent** and parameters recorded. Keep the
  raw image untouched; never overwrite originals.
- **Tests:** idempotence (running twice = running once); output retains the
  membrane reference; output is non-empty and plausibly sized.

### Stage 3 — Transcribe (`src/transcribe/`)
- **In:** cleaned images.
- **Out:** Latin transcript text in `output/transcripts/`, one file per
  membrane, plus a per-run manifest (model id, prompt version, parameters).
- The actual model call sits behind `model_client.py` (a thin adapter) so the
  backend is swappable and credentials come only from environment variables.
- Two-pass option: (a) diplomatic transcription preserving abbreviations, then
  (b) an expansion pass applying documented abbreviation rules. Keep both
  outputs; the diplomatic one is the honest record.
- The prompt is versioned and stored in the repo (`src/transcribe/prompts/`).
- **Tests:** adapter returns text for a fixture image (mock the model in CI);
  manifest is written; abbreviation-expansion rules behave on known inputs.

### Stage 4 — Score (`src/score/`)  ← build early
- **In:** a transcript + the matched Maitland ground-truth page (via the
  concordance).
- **Out:** a CER/WER report in `output/scores/`.
- Normalise both texts consistently before comparison (case, whitespace,
  punctuation, u/v and i/j, expanded vs diplomatic) and **state the
  normalisation**, since it changes the number. Use `jiwer` or a documented
  Levenshtein. Report character error rate and word error rate, plus a few
  example error lines.
- Build this stage on a tiny hand-made string pair first, before transcription
  quality is anywhere near good, to prove the measurement loop.
- **Tests:** known string pairs give known CER/WER; normalisation is applied
  symmetrically to both texts.

### Stage 5 — Structure (`src/structure/`)
- **In:** a transcript.
- **Out:** one CSV row per case in `output/metrics/`, with provenance columns.
- Target fields (nullable; absence is data): `membrane_ref`, `hundred`, `vill`,
  `case_type` (crown plea / civil plea / assize), `offence`, `parties`,
  `presenting_jury`, `verdict`, `amercement_value`, `deodand`, `notes`,
  `confidence`, `source_line_ref`.
- May use a second model pass to parse, but the parse is itself fallible:
  carry a `confidence` field and keep the `source_line_ref` so any figure can be
  traced back to the transcript line and thence to the membrane.
- **Tests:** parsing a fixed sample transcript yields the expected rows;
  provenance columns are always populated; amercement parsing handles medieval
  money forms (e.g. marks, shillings, pence) correctly.

### Stage 6 — Collate (`src/collate/`)
- **In:** the structured CSVs.
- **Out:** summary metrics and simple plots (`output/metrics/`).
- pandas: offence-type frequencies, amercement totals and distributions by
  hundred/vill, presentment counts, simple re-offending candidates. Re-offending
  must be treated cautiously — see §4.2 record-linkage risk.
- **Tests:** aggregations on a fixed small CSV give known totals.

### Stage 7 — Publish (`src/publish/`)
- **In:** the score report and the collation metrics/plots from stages 4 and 6.
- **Out:** a single self-contained `site/index.html` (plus `.nojekyll`),
  deployable to GitHub Pages.
- **Purpose:** a lightweight, public **proof-of-concept** page summarising the
  *derived quantitative metrics* and the method — a shareable URL for
  supervisors and a citable demonstration that the pipeline works. This page is
  explicitly temporary: the eventual home for the project is university
  infrastructure, so build the simplest thing that conveys the result, not a
  polished or permanent site.
- **Keep it minimal.** One generated HTML page, inline or single CSS file, no
  JS framework, no build toolchain, no server-side code. A small Python script
  renders `index.html` from the latest outputs so the page stays reproducible
  and in step with the numbers.
- **What the page shows:** the research question in a sentence or two; the
  method in brief (the pipeline stages); the **headline error rate (CER/WER),
  stated plainly**; and the **aggregate derived metrics** — offence-type
  frequencies, amercement distributions by hundred/vill, presentment counts —
  as simple tables or plots. Short quotations from Maitland (public domain) are
  fine for illustration.
- **What the page does not show:** no AALT or other copyrighted images (link to
  them at source — this is a copyright point, not a privacy one); the payload is
  derived metrics and method, not manuscript images.
- **One judgement call to leave to the user:** publishing a metric is a small
  act of publication. If any single finding is novel enough that it should first
  appear in the thesis or a paper, keep that one off the page. Aggregate
  proof-of-concept metrics are normally fine and helpful to show; if a specific
  result looks genuinely novel, flag it to the user rather than publishing it
  silently.
- **Tests:** the build script produces a valid, self-contained `site/index.html`
  from a fixed set of sample outputs; no `data/images_*` files are copied into
  `site/`; the headline CER/WER on the page matches the score report exactly.

See Appendix A for free hosting (GitHub Pages) setup.

---

## 4. Known risks and how to handle them

### 4.1 Transcription accuracy on court hand
A general multimodal model is **not** a model trained on medieval documentary
hands. Expect a meaningful error rate, worst on the most heavily abbreviated
passages. Mitigation: report it honestly; identify which abbreviation/hand
features drive errors; frame the result as a baseline ("what untuned multimodal
HTR achieves here"), which is a legitimate finding.

### 4.2 Record linkage / unstable naming
Medieval names are unstable (spelling variants, patronymics, toponymic bynames,
Latin vs vernacular forms). Any "same person re-offending" metric is a
hypothesis, not a fact. Flag candidates; never assert identity from name match
alone. Keep this caveat visible in any re-offending output.

### 4.3 Concordance / alignment
A bad image↔page match silently corrupts every score. The concordance
(§2.4) must be built and spot-checked by hand before scores are believed.

### 4.4 Money and quantity parsing
Amercement values appear in marks, shillings, pence and Latin numeral forms.
Centralise this parsing in one documented module with tests; do not scatter
ad-hoc number handling.

### 4.5 The model is the instrument, not the authority
Stated throughout: model output (transcription *and* structuring) is measured,
caveated, and traceable. This is the project's epistemic backbone and its
defensibility in a viva.

---

## 5. Build order (recommended)

1. Repo scaffold, `requirements.txt`, `.gitignore` (ignore `data/images_*`),
   `README.md` quickstart.
2. **Stage 4 (score)** on a toy string pair — prove the measurement loop.
3. Ground-truth extraction: pull the relevant Maitland pages' Latin into
   `data/ground_truth/`, one file per page.
4. `data/concordance.csv` for at least one membrane (manual + spot-check).
5. Stage 1 (harvest) for that one membrane.
6. Stage 2 (preprocess).
7. Stage 3 (transcribe), diplomatic pass first.
8. Run Stage 4 for real: first honest CER/WER. Write `output/scores/REPORT.md`.
9. Stage 5 (structure) on that membrane's transcript.
10. Stage 6 (collate) once a few membranes exist.
11. Stage 7 (publish) — generate the static site and deploy to GitHub Pages
    (Appendix A) once there is a real result worth sharing with supervisors.

Stop after step 8 if needed: a single reported error rate on one real membrane,
with the validation regime documented, already substantiates the application's
core methodological claim. Steps 9–10 strengthen it.

---

## 6. Out of scope (for now)

- Fine-tuning or training a custom HTR model.
- Full-eyre processing (the pilot is a handful of membranes).
- Translation into English (Stenton/Watson territory; later phase).
- Cross-county comparison (Somerset, Devon) — later phase.
- Any paid OCR/HTR service, including credit-limited tiers.
- Any paid hosting. Publishing is via free static hosting (GitHub Pages) only.

---

## 7. Definition of done

Per `CLAUDE.md`: one documented command sequence that, for at least one
confirmed membrane, harvests → preprocesses → transcribes → scores (CER/WER vs
Maitland) → emits a structured CSV, plus `output/scores/REPORT.md` stating the
error rate, the failures, and the hand/abbreviation features behind them. That
report is the artefact the PhD application draws on. Once a real result exists,
Stage 7 publishes it as a shareable web page (Appendix A).

---

## Appendix A — Free hosting with GitHub Pages

GitHub Pages hosts static sites directly from a GitHub repository at no cost,
over HTTPS, on a global CDN. Because the project is already a git repository,
publishing is just a matter of enabling Pages and pushing the generated `site/`.

### A.1 Why GitHub Pages
- **Free** for public repositories; no server, no card, no maintenance.
- Native to the git workflow already in use — push and the site updates.
- HTTPS and a CDN are provided automatically.
- Static-only (HTML/CSS/JS), which is exactly what Stage 7 produces. No
  databases or server-side code, which this project does not need.

### A.2 One-time setup
1. Create a repository on GitHub and add it as the `origin` remote (the user
   does this; per `CLAUDE.md`, Claude Code does not create remotes or push
   without explicit instruction).
2. Decide the publishing source. Simplest for this project: serve from the
   `/site` (or `/docs`) folder on the `main` branch. Alternatively serve from a
   dedicated `gh-pages` branch. Pick one and record it in the README.
3. In the repository's **Settings → Pages**, set the source branch and folder,
   and save.
4. Ensure a `.nojekyll` empty file sits in the publish folder so the raw static
   files are served without Jekyll processing.
5. After a minute or two the site is live at
   `https://<username>.github.io/<repository-name>/`. Share that URL with
   supervisors.

### A.3 Routine publishing (per update)
1. Run the Stage 7 build script to regenerate `site/` from the latest outputs.
2. Review locally (open `site/index.html` in a browser).
3. **Confirm with the user, then commit** the regenerated site (per the git
   rules in `CLAUDE.md`).
4. The user pushes to GitHub; Pages redeploys automatically within a minute or
   two.

### A.4 What goes on the public page
This page is a public proof-of-concept of **derived metrics** — it is meant to
be public, so there is no privacy problem to manage, only two simple checks:
- **No copyrighted images.** Don't republish AALT or other manuscript images;
  link to them at source. Public-domain Maitland (1884) text may be quoted.
- **Mind genuine novelty.** Publishing a metric is a small act of publication.
  Aggregate proof-of-concept numbers are normally fine and helpful to show; if a
  specific result looks novel enough to belong first in the thesis or a paper,
  flag it to the user rather than publishing it silently.

The page is temporary by design: it is superseded later by university
infrastructure. Build the lightest thing that demonstrates the result.

### A.5 Alternatives (also free, if ever needed)
- **GitLab Pages** and **Codeberg Pages** — equivalent static hosting if the
  repo lives there instead.
- **Netlify** / **Cloudflare Pages** free tiers — more features (deploy previews,
  custom build steps) than needed here, but viable. They add an external account
  and a build pipeline, which is why GitHub Pages is preferred for simplicity and
  for keeping everything in one place.
