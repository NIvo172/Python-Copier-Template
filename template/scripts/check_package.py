"""Build and validate source and wheel distributions."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"


def run(*command: str) -> None:
    """Run a command from the project root."""
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> int:
    """Build distributions and validate their metadata and wheel contents."""
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    run("uv", "build")

    source_distributions = sorted(DIST_DIR.glob("*.tar.gz"))
    wheels = sorted(DIST_DIR.glob("*.whl"))
    distributions = [*source_distributions, *wheels]
    if not source_distributions or not wheels:
        raise RuntimeError("The build did not produce both a source distribution and a wheel.")

    run(sys.executable, "-m", "twine", "check", "--strict", *(str(path) for path in distributions))
    for wheel in wheels:
        run("check-wheel-contents", str(wheel))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
