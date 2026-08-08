"""Sphinx configuration for the template repository documentation."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_project_metadata() -> dict[str, Any]:
    """Load the template's PEP 621 project metadata."""
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    project_metadata = pyproject.get("project")
    if not isinstance(project_metadata, dict):
        raise RuntimeError("pyproject.toml does not contain a [project] table.")
    return project_metadata


project_metadata = load_project_metadata()
project = str(project_metadata["name"])
release = str(project_metadata["version"])
version = release
author = "Template maintainers"

extensions = [
    "myst_parser",
    "sphinx_copybutton",
]

exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]
nitpicky = True
myst_heading_anchors = 3

html_theme = "furo"
html_title = "Python Project Copier Template"

copybutton_prompt_text = r"^(?:\$ |>>> |\.\.\. )"
copybutton_prompt_is_regexp = True
