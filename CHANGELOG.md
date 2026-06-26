# Changelog

All notable changes to this project are documented here.
Format loosely follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Unreleased]

### Added
- Initial repository scaffold: directory structure, `.gitignore`, `requirements.txt`, `README.md`
- Stage 4 scorer (`src/score/`): CER/WER computation with medieval Latin normalisation
  (lowercase, u→v, j→i, punctuation stripping)
- Tests for scorer on known string pairs
- Placeholder `data/concordance.csv` (unverified; V1–V3 verification pending)
