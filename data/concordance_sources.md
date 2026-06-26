# concordance_sources.md — evidence for data/concordance.csv

This file records the human-verified evidence behind each mapping in the
concordance. It is what lets a supervisor or viva panel confirm the mapping
is sound rather than asserted.

---

## V1 — TNA piece identity

**Piece confirmed: JUST 1/271** (1221 Gloucestershire eyre, crown pleas)

Maitland's introduction (pp. xliii–xlv of the 1884 edition; lines 4505–4553
of the Internet Archive DjVu OCR) describes two rolls:

> "There are in the Record Office two rolls containing the Gloucestershire
> business of this eyre. Let them be called A and B.
>
> Roll A is among the Coram Rege Rolls, and may be had by asking for Coram
> Rege Roll, Henry 3, No. 13. It is a set of 24 membranes. [...] With the
> tenth [membrane] this transcript begins."
>
> "Roll B is among the Assize Rolls and is known as Assize Roll M 141 [OCR
> damaged]. It is a set of 20 membranes. [...] With the eighth begin the
> pleas of the crown, which come to an end on the nineteenth."

**Finding:** Roll A (Coram Rege Roll Henry 3 No. 13) is NOT the JUST 1 series.
Roll B (Assize Roll) is the JUST 1 series piece.

AALT's piece JUST 1/271 is the assize roll for the 1221 Gloucestershire eyre
(AALT path `/AALT4/JUST1/JUST1no271/`), confirming it is Roll B. The AALT
fronts folder runs from IMG_3855 to IMG_3909 (55 images), which substantially
exceeds Roll B's 20 membranes — this discrepancy warrants investigation.
It is possible that:
- Multiple rolls (civil + crown) are imaged in the same AALT folder, or
- The roll was photographed with blank/title membranes that inflate the count.

The V3 anchor (below) proves the mapping is correct regardless.

**Caution on Roll A:** Maitland used BOTH rolls as cross-checks and his edition
synthesises them. The AALT images (JUST 1/271) are exclusively Roll B (the
assize roll). In cases where the two rolls diverged, Maitland's printed text
may favour Roll A readings over Roll B. This means the ground truth in
`data/ground_truth/` reflects Maitland's composite edition, not purely the
Roll B images we are transcribing. The CER/WER scores therefore measure
_transcript vs. Maitland edition_, not _transcript vs. identical physical text_.
This limitation must be stated explicitly in any report.

---

## V2 — AALT image folder and numbering scheme

**Confirmed by:** browsing AALT JUST 1 Henry III index, 2026-06-26.

**Piece folder:** `http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271/`

**Subfolders:**
- Fronts (membrane faces): `aJUST1no271fronts/`
  - Images: `IMG_3855.JPG` – `IMG_3909.JPG`
- Dorses (membrane reverses): `bJUST1no271dorses/`
  - Images: `IMG_3910.JPG` – `IMG_3955.JPG`

**Image URL pattern (HTML viewer page, not raw JPEG):**
```
http://aalt.law.uh.edu/AALT4/JUST1/JUST1no271/{subfolder}/IMG_{num}.htm
```

**Membrane ref scheme adopted:**
- m{N} = the N-th front image: IMG_(3854 + N)
  e.g. m1 = IMG_3855, m24 = IMG_3878
- m{N}d = the N-th dorse image: IMG_(3909 + N)
  e.g. m24d = IMG_3933, m38d = IMG_3947

---

## V3 — Spot-check alignment

**Status: PASSED — confirmed anchor established 2026-06-26**

The user confirmed that **AALT IMG_3878** (our ref m24, the 24th front image
in the JUST 1/271 folder) is the starting point for Maitland's Latin
transcription of the crown pleas.

**Cross-check against Maitland text:** The ground truth file `data/ground_truth/m24.txt`
extracted from the Internet Archive DjVu OCR begins with plea 1:
> "Willelmus le Cornur de Swelle occidit Willelmum Molendinarium..."

This is identically the opening of Maitland's `[Memb. 10.]` section in
his printed edition (p. 1 of the Latin text), confirming:

| Maitland marker | Our ref | AALT image | Verified |
|-----------------|---------|------------|---------|
| Memb. 10        | m24     | IMG_3878   | yes     |

**Arithmetic derivation for remaining membranes:**

From the confirmed anchor, adjacent membranes follow the formula:
- Maitland Memb. N face  → our ref m(N+14), AALT IMG_(3868+N)
- Maitland Memb. N dorse → our ref m(N+14)d, AALT IMG_(3923+N)

These 24 further rows in `data/concordance.csv` are marked `verified=pending`.
Each should be spot-checked (open the AALT image; confirm a distinctive plea
near the membrane break matches Maitland's text at that marker) before its
score is reported.

**Next spot-checks recommended (lowest marginal effort):**
1. m24d (Memb. 10 dors.) — consecutive with the confirmed anchor
2. m25 (Memb. 11) — first new membrane after the anchor
3. A membrane near the middle (e.g. m30 / Memb. 16) to catch any drift

**Known caveat:** AALT JUST 1/271 has 55 front images but Roll B has only 20
membranes. This means:
- Membranes 1–9 of Roll B (civil business) correspond to m1–m9 in AALT
- But our m24 = Memb. 10 of Roll B implies 14 images precede it, not 9
- The discrepancy is unexplained: there may be civil-business membranes,
  blank membranes, or images from an adjacent roll in the same AALT folder
- This does NOT invalidate the confirmed anchor (user observed the match
  directly); it is flagged here as a question for archival investigation
