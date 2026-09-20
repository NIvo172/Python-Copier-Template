"""Shared helpers for rendering the template and inspecting the result."""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from copier import run_copy

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
CURRENT_PYTHON = f"{sys.version_info.major}.{sys.version_info.minor}"

BASE_ANSWERS: dict[str, object] = {
    "project_name": "Example Project",
    "project_description": "Example generated project",
    "distribution_name": "example-project",
    "package_name": "example_project",
    "user_name": "Example Author",
    "user_email": "author@example.com",
    "repository_url": "https://github.com/example/example-project",
    "homepage_url": "https://example-project.example",
    "documentation_url": "https://docs.example-project.example",
    "changelog_url": "https://github.com/example/example-project/blob/main/CHANGELOG.md",
    "minimum_python_version": "3.11",
    "python_versions": ["3.11", "3.12", "3.13", "3.14"],
    "project_kind": "library",
    "docstring_style": "google",
    "use_docs": True,
    "use_notebooks": False,
    "use_dvc": False,
    "use_uml": False,
    "use_example_gallery": False,
    "use_precommit": True,
    "use_vscode": True,
    "ci_provider": "github",
    "has_other_contributors": False,
}


CASES: list[dict[str, object]] = [
    {"build_backend": "hatchling"},
    {"build_backend": "setuptools", "docstring_style": "numpy"},
    {
        "build_backend": "hatchling",
        "project_kind": "data_science",
        "docstring_style": "numpy",
        "use_notebooks": True,
        "use_dvc": True,
        "use_uml": True,
        "use_example_gallery": True,
        "has_other_contributors": True,
        "code_owners": "@example/full-data-science-maintainers",
    },
    {
        "build_backend": "setuptools",
        "use_docs": False,
        "use_precommit": False,
        "use_vscode": False,
        "ci_provider": "none",
    },
    {
        "build_backend": "hatchling",
        "ci_provider": "gitlab",
        "has_other_contributors": True,
        "code_owners": "@example/maintainers",
    },
    {
        "build_backend": "setuptools",
        "ci_provider": "bitbucket",
        "has_other_contributors": True,
        "code_owners": "@example/maintainers",
    },
]

CASE_IDS = ["pyproject-hatchling", "setuptools-numpy", "data-science-full", "none-no-ci", "gitlab-coe", "bitbucket-coe"]

NORMAL_PROJECT_REGRESSION_OVERRIDES: dict[str, object] = {
    "minimum_python_version": CURRENT_PYTHON,
    "python_versions": [CURRENT_PYTHON],
    "build_backend": "hatchling",
    "project_kind": "data_science",
    "use_docs": True,
    "use_notebooks": True,
    "use_dvc": True,
    "use_uml": True,
    "use_example_gallery": True,
    "use_precommit": True,
    "use_vscode": True,
    "ci_provider": "none",
    "has_other_contributors": False,
}


def render_generated_project(destination: Path, overrides: dict[str, object]) -> dict[str, object]:
    """Render one generated-project variant and return its complete answers."""
    answers = BASE_ANSWERS | overrides
    copy_options: dict[str, object] = {}
    if (TEMPLATE_ROOT / ".git").exists():
        copy_options["vcs_ref"] = "HEAD"

    run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=destination,
        data=answers,
        defaults=True,
        overwrite=True,
        **copy_options,
    )
    return answers


def load_toml(destination: Path, relative: str = "pyproject.toml") -> dict[str, object]:
    return tomllib.loads((destination / relative).read_text(encoding="utf-8"))


def has_dependency(dependencies: list[object], prefix: str) -> bool:
    return any(isinstance(dependency, str) and dependency.startswith(prefix) for dependency in dependencies)


def generated_documentation(destination: Path) -> list[Path]:
    """Return user-facing Markdown documents from a generated project."""
    documents = [destination / name for name in ("README.md", "CONTRIBUTING.md", "MAINTAINING.md")]
    docs_directory = destination / "docs"
    if docs_directory.is_dir():
        documents.extend(sorted(docs_directory.rglob("*.md")))
    return documents


def case_cache_id(overrides: dict[str, object]) -> str:
    """Stable cache key for a set of case overrides (used by the rendered-project cache)."""
    import hashlib
    import json

    payload = json.dumps(
        {k: v for k, v in sorted(overrides.items(), key=lambda kv: str(kv[0]))},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


def case_id_for(overrides: dict[str, object]) -> str:
    """Return the stable `CASE_IDS` label for a set of `CASES` overrides."""
    for case, label in zip(CASES, CASE_IDS, strict=True):
        if case == overrides:
            return label
    raise KeyError(f"No case id for overrides {sorted(overrides)!r}")
