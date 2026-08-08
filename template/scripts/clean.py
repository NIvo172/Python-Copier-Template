"""Remove generated project artifacts in a cross-platform way."""

from pathlib import Path
from shutil import rmtree

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = (
    ROOT / "build",
    ROOT / "dist",
    ROOT / "reports" / "coverage",
    ROOT / "reports" / "pytest",
    ROOT / "reports" / "sphinx",
    ROOT / "docs" / "_build",
    ROOT / "docs" / "source" / "_autosummary",
    ROOT / "docs" / "source" / "auto_examples",
)
FILES = (
    ROOT / "docs" / "source" / "sg_execution_times.rst",
    ROOT / "docs" / "source" / "diagrams" / "classes.mmd",
    ROOT / "docs" / "source" / "diagrams" / "packages.mmd",
)


def main() -> None:
    """Delete generated directories and files if present."""
    for directory in DIRECTORIES:
        rmtree(directory, ignore_errors=True)
    for file_path in FILES:
        file_path.unlink(missing_ok=True)
    (ROOT / ".coverage").unlink(missing_ok=True)
    for coverage_fragment in ROOT.glob(".coverage.*"):
        coverage_fragment.unlink(missing_ok=True)
    for pytest_temporary_directory in ROOT.glob("pytest-of-*"):
        rmtree(pytest_temporary_directory, ignore_errors=True)


if __name__ == "__main__":
    main()
