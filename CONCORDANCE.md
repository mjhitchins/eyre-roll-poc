# CONCORDANCE.md — building and verifying the image↔edition mapping

The concordance is the linchpin of this project (see `SPEC.md` §2.4). A score is
only meaningful if the AALT membrane image and the Maitland page transcribe the
**same physical text**. This file is the checklist for building
`data/concordance.csv` and the verification it must pass before any CER/WER
number is trusted.

This is partly manual scholarly work. The pipeline depends on the concordance
but cannot fully produce it. Record uncertainty explicitly rather than guessing.

---

## The mechanism

Maitland's 1884 edition prints **membrane numbers in the margin** (e.g. "m. 1",
"m. 1d" for the dorse/back of membrane 1) marking where each membrane begins in
the roll. AALT's images are named per membrane face. The concordance is the
mapping between the two:

> Maitland marginal "m. N" (and the pleas printed under it)
> ↔ the AALT image(s) of membrane N (face) and N dorse of the same TNA piece.

That marginal-membrane notation is the concordance key. It is what makes the
mapping buildable at membrane granularity instead of by page-by-page eyeballing.

---

## Three verifications to perform before trusting the mapping

Do these in order. Do not proceed to scoring until all three pass.

### V1 — Confirm the correct TNA piece (JUST 1 series)

Maitland transcribed a specific roll held at The National Archives in the
**JUST 1** assize-roll series. The commonly cited piece for the 1221
Gloucestershire eyre is **JUST 1/274**, but this MUST be verified, not assumed —
a wrong piece silently corrupts every downstream score.

- Read Maitland's own preface on the Internet Archive scan
  (`crowncountyplea00glouuoft`) and record exactly which PRO/TNA roll he states
  he used, in his own words, with the scan page number.
- Cross-check that statement against the TNA Discovery catalogue entry for the
  candidate JUST 1 piece (confirm county = Gloucestershire, eyre date = 1221,
  justices consistent with Maitland's title page).
- **Caveat to resolve here:** Maitland's edition covers the **crown pleas**, not
  necessarily the entire eyre roll. The full eyre was later edited by Stenton
  (Selden Society vol. 59, 1940). Confirm whether the AALT piece you are pulling
  is the same roll/membranes Maitland used, or a different roll of the same eyre.
  Note explicitly which pleas Maitland's text does and does not cover.
- Record the confirmed piece reference and the evidence for it in
  `data/concordance_sources.md`.

### V2 — Confirm that piece is present in AALT and get its image folder

- Locate the piece in the AALT JUST 1 Henry III index
  (`http://aalt.law.uh.edu/JUST1/JUST1_H3Lo.html`).
- Record the AALT image-folder URL for the piece. AALT image URLs follow the
  pattern (observed in cited scholarship):
  `http://aalt.law.uh.edu/{collection}/{reign}/{piece}/{subfolder}/IMG_####.htm`
  e.g. `.../AALT1/H3/JUST1no274/.../IMG_0001.htm` (confirm the exact path for
  the actual piece; do not assume the numbers above).
- Note the image numbering scheme and how it relates to membrane faces/dorses
  (AALT often photographs faces in one run and dorses in another, or interleaves
  them — establish which, for THIS piece, before mapping).
- **Crown copyright:** AALT states its digitized images remain under crown
  copyright. They are fine to view and to transcribe from, but are **not** to be
  republished on the public proof-of-concept site (link to source instead). See
  `SPEC.md` Stage 7.

### V3 — Anchor with a known plea (spot-check the alignment)

Before mapping the whole piece, prove the mapping on one membrane:

- Pick one distinctive, identifiable plea early in Maitland (a named person,
  place, or unusual detail under a specific "m. N").
- Open the corresponding AALT membrane image and confirm by eye that the text
  begins/sits where Maitland's marginal note says it should. (This is the
  irreducible manual step — a human must look at both.)
- If the distinctive plea lines up, the membrane offset is confirmed for that
  membrane. If it does not, the offset is wrong — recheck V1 (piece) and the
  AALT numbering scheme (V2) before going further.
- Record the spot-check (which plea, which Maitland page, which AALT image,
  outcome) in `data/concordance_sources.md`.

---

## `data/concordance.csv` schema

One row per membrane face (or dorse). Columns:

| column                | meaning                                                        |
|-----------------------|----------------------------------------------------------------|
| `membrane_ref`        | canonical membrane id, e.g. `m1`, `m1d`, `m2`                  |
| `tna_piece`           | confirmed TNA reference, e.g. `JUST 1/274`                     |
| `aalt_image_url`      | full AALT image-page URL for this membrane face               |
| `aalt_image_filename` | the `IMG_####` filename (harvest filename anchor)             |
| `maitland_page_start` | first Maitland printed page covering this membrane            |
| `maitland_page_end`   | last Maitland printed page covering this membrane             |
| `maitland_archive_id` | `crowncountyplea00glouuoft` (constant; provenance)            |
| `pleas_covered`       | Maitland plea numbers on this membrane, if numbered           |
| `coverage`            | `full` / `partial` / `crown-pleas-only` / `none`              |
| `verified`            | `yes` / `no` — has V3 spot-check passed for this membrane?    |
| `confidence`          | `high` / `medium` / `low`                                     |
| `notes`               | anything uncertain: damage, gaps, ambiguous numbering, etc.   |

Rules:
- A row with `verified = no` must never be used to compute a reported score.
- `confidence = low` rows are research questions, not facts — flag, don't bury.
- Absence is data: if Maitland does not cover a membrane, record it as
  `coverage = none` rather than omitting the row.

---

## `data/concordance_sources.md`

A short prose companion recording the evidence behind the CSV:
- Maitland's exact statement of his manuscript source (quote ≤15 words + scan
  page ref).
- The TNA Discovery entry consulted and what it confirmed.
- The AALT index URL and image-numbering scheme for the piece.
- Each V3 spot-check performed and its outcome.

This file is what lets a supervisor (or a viva panel) check that the mapping is
sound rather than asserted.

---

## Definition of done for the concordance (pilot)

At least **one** membrane row in `data/concordance.csv` with `verified = yes`
and `confidence = high`, backed by a V1–V3 record in
`data/concordance_sources.md`. That single verified membrane is enough to run
the rest of the pilot pipeline honestly. Extend to more membranes once the
mapping method is proven on one.
