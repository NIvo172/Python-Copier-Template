"""Verify that exploratory notebooks contain no removable output or metadata."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_ROOT = ROOT / "notebooks"


def main() -> None:
    """Run nbstripout in verification mode for each exploratory notebook."""
    notebooks = sorted(NOTEBOOK_ROOT.rglob("*.ipynb"))
    if not notebooks:
        return

    subprocess.run(
        ["nbstripout", "--verify", *(str(path) for path in notebooks)],
        cwd=ROOT,
        check=True,
    )


if __name__ == "__main__":
    main()
