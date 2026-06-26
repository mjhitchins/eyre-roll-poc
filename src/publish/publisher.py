"""
Stage 7: Publish database to docs/ for GitHub Pages.

Copies output/eyre1221.db to docs/eyre1221.db and ensures .nojekyll exists.
The docs/index.html is a static file committed to the repo; only the DB changes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_SRC = REPO_ROOT / "output" / "eyre1221.db"
SITE_DIR = REPO_ROOT / "docs"


def publish(db_path: Path = DB_SRC, site_dir: Path = SITE_DIR) -> Path:
    site_dir.mkdir(parents=True, exist_ok=True)
    dest = site_dir / "eyre1221.db"
    shutil.copy2(db_path, dest)
    (site_dir / ".nojekyll").touch()
    return dest
