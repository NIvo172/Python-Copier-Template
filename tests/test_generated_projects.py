from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from urllib.parse import unquote

import pytest
import yaml
from copier import run_copy, run_update
from jinja2 import Environment

TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MYST_INCLUDE = re.compile(r"^```\{include\}\s+(.+?)\s*$", re.MULTILINE)
SCRIPT_REFERENCE = re.compile(r"\b(scripts/[a-zA-Z0-9_-]+\.py)\b")
TOCTREE = re.compile(r"```\{toctree\}\s*\n(.*?)```", re.DOTALL)
TOX_ENVIRONMENT_REFERENCE = re.compile(r"\btox run -e ([a-zA-Z0-9_-]+)\b")
EXTERNAL_LINK_PREFIXES = ("http://", "https://", "mailto:")

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


def test_docstring_style_default_is_google() -> None:
    copier_config = (TEMPLATE_ROOT / "copier.yml").read_text()
    section = copier_config.split("\ndocstring_style:\n", maxsplit=1)[1]
    section = section.split("\nuse_docs:\n", maxsplit=1)[0]
    assert "  default: google" in section


def test_questions_use_plain_prompt_markers() -> None:
    copier_config = yaml.safe_load((TEMPLATE_ROOT / "copier.yml").read_text())
    question_names = {
        key
        for key, value in copier_config.items()
        if not key.startswith("_") and isinstance(value, dict) and "type" in value
    }
    assert question_names
    assert all(copier_config[name].get("qmark") == ">" for name in question_names)


def test_template_documentation_separates_landing_and_reference_content() -> None:
    readme = (TEMPLATE_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (TEMPLATE_ROOT / "docs/architecture.md").read_text(encoding="utf-8")
    maintenance = (TEMPLATE_ROOT / "docs/maintenance.md").read_text(encoding="utf-8")

    assert len(readme.splitlines()) < 250
    for guide in (
        "docs/README.md",
        "docs/getting-started.md",
        "docs/template-options.md",
        "docs/architecture.md",
        "docs/command-reference.md",
        "docs/ci-and-collaboration.md",
        "docs/data-science.md",
        "docs/maintenance.md",
        "docs/updates-and-releases.md",
        "docs/troubleshooting.md",
    ):
        assert guide in readme
        assert (TEMPLATE_ROOT / guide).is_file()

    assert "Tox is the public task API" in architecture
    assert "Tox selects these groups through `dependency_groups`" in architecture
    assert "should not normally be repeated under Tox `deps`" in architecture
    assert "`scripts/init_project.py` | Always | One-time bootstrap" in architecture
    assert "`scripts/clean.py` | Always | Recurring maintenance" in architecture
    assert "`scripts/check_package.py` | Always | Recurring validation" in architecture
    assert "## Bootstrap a generated project" in maintenance
    assert "copier update --pretend --vcs-ref=:current:" in maintenance
    assert "versioned migration" in maintenance


def test_post_copy_message_separates_initialisation_and_validation() -> None:
    copier_config = yaml.safe_load((TEMPLATE_ROOT / "copier.yml").read_text())
    message = copier_config["_message_after_copy"]

    assert "scripts/init_project.py" in message
    assert "scripts/setup_project.py" not in message
    assert "uv run --locked tox" in message
    assert '--git-name "Your Name"' in message
    assert '--git-email "you@example.com"' in message
    assert "John Doe <john.doe@example.com>" in message


def test_init_script_has_one_time_terminal_only_contract() -> None:
    script = (TEMPLATE_ROOT / "template/scripts/init_project.py").read_text()

    assert script.startswith('# /// script\n# requires-python = ">=3.11"\n# dependencies = []\n# ///')
    assert 'DEFAULT_GIT_NAME = "John Doe"' in script
    assert 'DEFAULT_GIT_EMAIL = "john.doe@example.com"' in script
    assert 'DEFAULT_TAG = "v0.0.1"' in script
    assert "setup_" not in script
    assert '["uv", "run", "--locked", "tox"]' not in script
    assert '["uv", "run", "dvc", "repro"]' in script
    assert '["git", "init", "--initial-branch=main"]' in script
    assert "run_precommit_until_clean()" in script
    assert "def worktree_fingerprint()" in script
    assert "str(path.readlink()).encode" in script
    assert "os.readlink(" not in script
    assert "Pre-commit failed without modifying files; not retrying." in script
    assert 'environment.pop("VIRTUAL_ENV", None)' in script
    assert "capture_output=True" in script
    assert "ensure_clean_worktree()" in script
    assert "log_path" not in script
    assert "Tee" not in script
    assert "validate_reports" not in script


def test_python_version_default_tracks_minimum_version() -> None:
    copier_config = yaml.safe_load((TEMPLATE_ROOT / "copier.yml").read_text())
    default_template = Environment().from_string(copier_config["python_versions"]["default"])
    expected_defaults = {
        "3.11": ["3.11", "3.12", "3.13", "3.14"],
        "3.12": ["3.12", "3.13", "3.14"],
        "3.13": ["3.13", "3.14"],
        "3.14": ["3.14"],
    }

    for minimum_version, expected in expected_defaults.items():
        rendered = default_template.render(minimum_python_version=minimum_version)
        assert yaml.safe_load(rendered) == expected


CASES = [
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

CURRENT_PYTHON = f"{sys.version_info.major}.{sys.version_info.minor}"
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


def run(*command: str, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def command_output(*command: str, cwd: Path) -> str:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


def has_dependency(dependencies: list[object], prefix: str) -> bool:
    return any(isinstance(dependency, str) and dependency.startswith(prefix) for dependency in dependencies)


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


def generated_documentation(destination: Path) -> list[Path]:
    """Return user-facing Markdown documents from a generated project."""
    documents = [destination / name for name in ("README.md", "CONTRIBUTING.md", "MAINTAINING.md")]
    docs_directory = destination / "docs"
    if docs_directory.is_dir():
        documents.extend(sorted(docs_directory.rglob("*.md")))
    return documents


def test_copier_update_runs_versioned_migration_and_preserves_project_files(tmp_path: Path) -> None:
    template_repository = tmp_path / "template-repository"
    destination = tmp_path / "generated"
    shutil.copytree(
        TEMPLATE_ROOT,
        template_repository,
        ignore=shutil.ignore_patterns(
            ".git",
            ".venv",
            ".tox",
            ".pytest_cache",
            ".ruff_cache",
            ".generated",
            "__pycache__",
            "*.pyc",
            "dist",
            "pytest-of-root",
        ),
    )

    run("git", "init", "--initial-branch=main", cwd=template_repository)
    run("git", "config", "user.name", "Template Test", cwd=template_repository)
    run("git", "config", "user.email", "template-test@example.com", cwd=template_repository)
    run("git", "add", ".", cwd=template_repository)
    run("git", "commit", "-m", "Template v0.1.0", cwd=template_repository)
    run("git", "tag", "v0.1.0", cwd=template_repository)

    run_copy(
        src_path=str(template_repository),
        dst_path=destination,
        data=BASE_ANSWERS,
        defaults=True,
        overwrite=True,
        vcs_ref="v0.1.0",
    )

    project_notes = destination / "PROJECT_NOTES.md"
    project_notes.write_text("Project-owned content must survive Copier updates.\n", encoding="utf-8")
    run("git", "init", "--initial-branch=main", cwd=destination)
    run("git", "config", "user.name", "Project Test", cwd=destination)
    run("git", "config", "user.email", "project-test@example.com", cwd=destination)
    run("git", "add", ".", cwd=destination)
    run("git", "commit", "-m", "Generated from v0.1.0", cwd=destination)

    (template_repository / "template/UPGRADE_MARKER.txt.jinja").write_text(
        "Updated project: {{ project_name }}\n",
        encoding="utf-8",
    )
    copier_config = template_repository / "copier.yml"
    copier_config.write_text(
        copier_config.read_text(encoding="utf-8")
        + """

_migrations:
  - version: "0.2.0"
    command:
      - python
      - -c
      - >-
        from pathlib import Path;
        Path("migration-result.txt").write_text("migration completed", encoding="utf-8")
""",
        encoding="utf-8",
    )
    run("git", "add", ".", cwd=template_repository)
    run("git", "commit", "-m", "Template v0.2.0", cwd=template_repository)
    run("git", "tag", "v0.2.0", cwd=template_repository)

    run_update(
        dst_path=destination,
        vcs_ref="v0.2.0",
        defaults=True,
        overwrite=True,
        unsafe=True,
    )

    answers = yaml.safe_load((destination / ".copier-answers.yml").read_text(encoding="utf-8"))
    assert answers["_commit"] == "v0.2.0"
    assert answers["project_name"] == "Example Project"
    assert project_notes.read_text(encoding="utf-8") == "Project-owned content must survive Copier updates.\n"
    assert (destination / "UPGRADE_MARKER.txt").read_text(encoding="utf-8") == "Updated project: Example Project\n"
    assert (destination / "migration-result.txt").read_text(encoding="utf-8") == "migration completed"


@pytest.mark.parametrize("overrides", CASES)
def test_generated_documentation_references_are_valid(tmp_path: Path, overrides: dict[str, object]) -> None:
    """Validate links, commands, includes, and navigation in every rendered variant."""
    destination = tmp_path / "generated"
    answers = render_generated_project(destination, overrides)
    tox_config = (destination / "tox.ini").read_text(encoding="utf-8")
    tox_environments = set(re.findall(r"^\[testenv:([^]]+)\]$", tox_config, re.MULTILINE))
    failures: list[str] = []

    for document in generated_documentation(destination):
        text = document.read_text(encoding="utf-8")
        relative_document = document.relative_to(destination)

        for token in ("{{", "{%", "{#"):
            if token in text:
                failures.append(f"{relative_document}: unresolved template token {token!r}")

        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("#") or target.startswith(EXTERNAL_LINK_PREFIXES):
                continue
            path_text = unquote(target.split("#", maxsplit=1)[0])
            if path_text and not (document.parent / path_text).resolve().exists():
                failures.append(f"{relative_document}: missing link target {target}")

        if relative_document.is_relative_to(Path("docs/source")):
            for raw_target in MYST_INCLUDE.findall(text):
                target = raw_target.strip().strip("<>")
                if not (document.parent / target).resolve().exists():
                    failures.append(f"{relative_document}: missing include target {target}")

        for script in SCRIPT_REFERENCE.findall(text):
            if not (destination / script).is_file():
                failures.append(f"{relative_document}: missing script {script}")

        for environment in TOX_ENVIRONMENT_REFERENCE.findall(text):
            if environment not in tox_environments:
                failures.append(f"{relative_document}: missing Tox environment {environment}")

    if answers["use_docs"]:
        source_directory = destination / "docs/source"
        index = (source_directory / "index.md").read_text(encoding="utf-8")
        for block in TOCTREE.findall(index):
            for raw_entry in block.splitlines():
                entry = raw_entry.strip()
                if not entry or entry.startswith(":"):
                    continue
                if entry == "auto_examples/index":
                    if not answers["use_example_gallery"] or not (destination / "examples").is_dir():
                        failures.append("docs/source/index.md: gallery target has no example source")
                    continue
                candidates = [source_directory / f"{entry}{suffix}" for suffix in (".md", ".rst", ".ipynb")]
                if not any(candidate.is_file() for candidate in candidates):
                    failures.append(f"docs/source/index.md: missing toctree target {entry}")

    assert not failures, "Generated documentation failures:\n" + "\n".join(failures)


@pytest.mark.parametrize("overrides", CASES)
def test_generated_sphinx_command_reference_matches_selected_features(
    tmp_path: Path,
    overrides: dict[str, object],
) -> None:
    """Document every rendered Tox task without advertising unavailable features."""
    destination = tmp_path / "generated"
    answers = render_generated_project(destination, overrides)
    reference_path = destination / "docs/source/command-reference.md"

    if not answers["use_docs"]:
        assert not reference_path.exists()
        return

    reference = reference_path.read_text(encoding="utf-8")
    tox_config = (destination / "tox.ini").read_text(encoding="utf-8")
    tox_environments = set(re.findall(r"^\[testenv:([^]]+)\]$", tox_config, re.MULTILINE))

    assert "contains only commands supported" in reference
    for environment in tox_environments:
        assert f"tox run -e {environment}" in reference

    conditional_markers = {
        "use_precommit": "pre-commit install",
        "use_notebooks": "jupyter lab",
        "use_dvc": "dvc repro",
        "use_uml": "Generate UML only",
        "use_example_gallery": "Sphinx-Gallery examples",
    }
    for answer, marker in conditional_markers.items():
        assert (marker in reference) is bool(answers[answer])


@pytest.mark.parametrize("overrides", CASES)
def test_generated_project(tmp_path: Path, overrides: dict[str, object]) -> None:
    destination = tmp_path / "generated"
    answers = render_generated_project(destination, overrides)

    pyproject = tomllib.loads((destination / "pyproject.toml").read_text())
    assert pyproject["project"]["name"] == "example-project"
    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["project"]["urls"] == {
        "Homepage": "https://example-project.example",
        "Documentation": "https://docs.example-project.example",
        "Repository": "https://github.com/example/example-project",
        "Issues": "https://github.com/example/example-project/issues",
        "Changelog": "https://github.com/example/example-project/blob/main/CHANGELOG.md",
    }
    assert pyproject["tool"]["format_docstring"]["docstring_style"] == answers["docstring_style"]
    assert pyproject["tool"]["ruff"]["lint"]["pydocstyle"]["convention"] == answers["docstring_style"]
    assert has_dependency(pyproject["dependency-groups"]["lint"], "format-docstring")
    assert has_dependency(pyproject["dependency-groups"]["lint"], "pytest")
    package_check_dependencies = pyproject["dependency-groups"]["package-check"]
    assert has_dependency(package_check_dependencies, "check-wheel-contents")
    assert has_dependency(package_check_dependencies, "twine")
    test_dependencies = pyproject["dependency-groups"]["test"]
    assert has_dependency(test_dependencies, "pytest-reportlog")
    assert has_dependency(pyproject["dependency-groups"]["dev"], "pytest-sugar")
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    assert pyproject["tool"]["ruff"]["line-length"] == 121
    assert pyproject["tool"]["ruff"]["force-exclude"] is True
    assert pyproject["tool"]["format_docstring"]["line_length"] == 121
    assert pyproject["tool"]["ruff"]["format"]["docstring-code-format"] is True
    assert pyproject["tool"]["ruff"]["format"]["docstring-code-line-length"] == "dynamic"
    assert "G" in pyproject["tool"]["ruff"]["lint"]["select"]
    assert "LOG" in pyproject["tool"]["ruff"]["lint"]["select"]
    assert has_dependency(pytest_options["required_plugins"], "pytest-reportlog")
    assert "--report-log=reports/pytest/report.jsonl" in pytest_options["addopts"]
    assert "--cov=example_project" in pytest_options["addopts"]
    assert "--cov-report=html:reports/coverage/html" in pytest_options["addopts"]
    assert "--cov-report=xml:reports/coverage/coverage.xml" in pytest_options["addopts"]
    assert "--cov-report=json:reports/coverage/coverage.json" in pytest_options["addopts"]
    assert "--cov-branch" not in pytest_options["addopts"]
    assert pytest_options["log_cli"] is False
    assert pytest_options["log_file"] == "reports/pytest/logs/pytest.log"
    assert all(">=" in requirement for requirement in pytest_options["required_plugins"])
    assert (destination / "src/example_project/__init__.py").is_file()
    assert (destination / "tests/test_main.py").is_file()
    assert (destination / "tox.ini").is_file()
    assert (destination / "CONTRIBUTING.md").is_file()
    assert (destination / "MAINTAINING.md").is_file()
    renovate_config = json.loads((destination / "renovate.json").read_text(encoding="utf-8"))
    assert "enabledManagers" not in renovate_config
    assert renovate_config["lockFileMaintenance"]["enabled"] is True
    routine_updates = renovate_config["packageRules"][0]
    assert "matchManagers" not in routine_updates
    assert routine_updates["matchUpdateTypes"] == ["minor", "patch", "pin", "digest"]
    editorconfig = (destination / ".editorconfig").read_text()
    assert "[Makefile]" in editorconfig
    assert "indent_style = tab" in editorconfig
    tox_config = (destination / "tox.ini").read_text()
    generated_readme = (destination / "README.md").read_text(encoding="utf-8")
    contributing = (destination / "CONTRIBUTING.md").read_text(encoding="utf-8")
    maintaining = (destination / "MAINTAINING.md").read_text(encoding="utf-8")
    project_guides = "\n".join((generated_readme, contributing, maintaining))

    assert len(generated_readme.splitlines()) < 150
    assert not generated_readme.endswith("\n\n")
    assert not contributing.endswith("\n\n")
    assert not maintaining.endswith("\n\n")
    assert "uv sync --locked" in generated_readme
    assert "| `CONTRIBUTING.md` | Contributors | Environment setup" in generated_readme
    assert "| `MAINTAINING.md` | Maintainers | One-time bootstrap" in generated_readme
    assert "uv run scripts/init_project.py" not in generated_readme

    assert "# Contributing to Example Project" in contributing
    assert "Tox is the preferred project-level task interface" in contributing
    assert "| Task | Preferred Tox command | Direct command |" in contributing
    assert "uv run --locked tox run -e lint" in contributing
    assert "uv run --locked --group lint ruff check ." in contributing
    assert "build and test the installed wheel" in contributing

    assert "# Maintaining Example Project" in maintaining
    assert "uv run scripts/init_project.py" in maintaining
    assert "uv run --locked tox" in maintaining
    assert "## Tox and task-script architecture" in maintaining
    assert "selected by Tox through `dependency_groups`" in maintaining
    assert "Normal Tox and CI tasks do not call `init_project.py`." in maintaining
    assert "`scripts/clean.py` | Recurring maintenance" in maintaining
    assert "`scripts/check_package.py` | Recurring validation" in maintaining
    assert ("Strict Sphinx HTML/API coverage" in maintaining) is bool(answers["use_docs"])
    assert ("Pyreverse and Mermaid output" in maintaining) is bool(answers["use_docs"] and answers["use_uml"])
    assert ("Exploratory notebook output and metadata policy" in maintaining) is bool(answers["use_notebooks"])

    assert "https://docs.astral.sh/uv/" in project_guides
    assert "https://tox.wiki/" in project_guides
    assert "https://docs.pytest.org/" in project_guides
    assert "https://docs.astral.sh/ruff/" in project_guides
    assert "https://mypy.readthedocs.io/" in project_guides
    assert ("https://pre-commit.com/" in project_guides) is bool(answers["use_precommit"])
    assert ("https://jupyterlab.readthedocs.io/en/stable/" in project_guides) is bool(answers["use_notebooks"])
    assert ("https://www.sphinx-doc.org/en/master/" in project_guides) is bool(answers["use_docs"])
    assert ("https://dvc.org/doc" in project_guides) is bool(
        answers["project_kind"] == "data_science" and answers["use_dvc"]
    )
    assert ("https://docs.github.com/actions" in project_guides) is bool(answers["ci_provider"] == "github")
    assert ("https://docs.gitlab.com/ci/" in project_guides) is bool(answers["ci_provider"] == "gitlab")
    assert (
        "https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/" in project_guides
    ) is bool(answers["ci_provider"] == "bitbucket")
    assert ("tox run -e pre-commit" in contributing) is bool(answers["use_precommit"])
    assert ("tox run -e notebooks" in contributing) is bool(answers["use_notebooks"])
    assert ("tox run -e docs -- html" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e docs -- coverage" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e docs -- clean" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e dvc" in contributing) is bool(answers["project_kind"] == "data_science" and answers["use_dvc"])
    assert ("## Propose changes" in contributing) is bool(answers["has_other_contributors"])
    assert ("## Report bugs" in contributing) is bool(answers["has_other_contributors"])
    assert ("## Collaboration configuration" in maintaining) is bool(answers["has_other_contributors"])

    collaboration_paths = {
        "github": (
            ".github/CODEOWNERS",
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE/bug_report.yml",
        ),
        "gitlab": (
            ".gitlab/CODEOWNERS",
            ".gitlab/merge_request_templates/Default.md",
            ".gitlab/issue_templates/Bug.md",
        ),
        "bitbucket": (
            ".bitbucket/CODEOWNERS",
            ".bitbucket/pull_request_template.md",
        ),
    }
    all_collaboration_paths = {path for provider_paths in collaboration_paths.values() for path in provider_paths}
    expected_collaboration_paths = (
        set(collaboration_paths.get(str(answers["ci_provider"]), ())) if answers["has_other_contributors"] else set()
    )
    for path in all_collaboration_paths:
        assert (destination / path).is_file() is (path in expected_collaboration_paths)

    code_of_conduct = destination / "CODE_OF_CONDUCT.md"
    assert code_of_conduct.is_file() is bool(answers["has_other_contributors"])
    if answers["has_other_contributors"]:
        assert str(answers["code_owners"]) in (
            destination / collaboration_paths[str(answers["ci_provider"])][0]
        ).read_text(encoding="utf-8")
        assert "author@example.com" in code_of_conduct.read_text(encoding="utf-8")
        if answers["ci_provider"] == "github":
            bug_form = yaml.safe_load((destination / ".github/ISSUE_TEMPLATE/bug_report.yml").read_text())
            assert bug_form["name"] == "Bug report"
        elif answers["ci_provider"] == "bitbucket":
            assert "Bitbucket does not consume repository-defined issue templates" in contributing

    assert "[testenv:lock]" in tox_config
    assert "uv lock --check" in tox_config
    assert "[testenv:lint]" in tox_config
    assert "[testenv:package-check]" in tox_config
    assert "python scripts/check_package.py" in tox_config
    assert "[testenv:build]" in tox_config
    assert "[testenv:clean]" in tox_config
    assert "labels = test" in tox_config
    assert "uv build" in tox_config
    package_check_script = (destination / "scripts/check_package.py").read_text(encoding="utf-8")
    assert (destination / "scripts/check_package.py").is_file()
    assert "distributions = [*source_distributions, *wheels]" in package_check_script
    assert (destination / "scripts/init_project.py").is_file()
    assert not (destination / "scripts/setup_project.py").exists()
    assert has_dependency(pyproject["dependency-groups"]["dev"], "tox")
    assert has_dependency(pyproject["dependency-groups"]["dev"], "tox-uv")
    assert not list(destination.rglob("*.jinja"))

    autosummary_template_root = destination / "docs/source/_templates/autosummary"
    rendered_text = "\n".join(
        path.read_text(errors="ignore")
        for path in destination.rglob("*")
        if path.is_file() and path.stat().st_size < 1_000_000 and not path.is_relative_to(autosummary_template_root)
    )
    assert "coea" not in rendered_text
    assert "{{ package_name }}" not in rendered_text
    assert "{% if" not in rendered_text

    main_module = (destination / "src/example_project/main.py").read_text()
    if answers["docstring_style"] == "google":
        assert "    Args:" in main_module
        assert "    Parameters\n    ----------" not in main_module
    else:
        assert "    Parameters\n    ----------" in main_module
        assert "    Args:" not in main_module

    if answers["build_backend"] == "setuptools":
        assert pyproject["build-system"]["requires"] == [
            "setuptools>=80",
            "setuptools-scm[simple]>=10.2",
        ]
        assert "setuptools" not in pyproject.get("tool", {})
        assert "setuptools_scm" not in pyproject.get("tool", {})

    if answers["use_precommit"]:
        precommit = (destination / ".pre-commit-config.yaml").read_text()
        assert "jsh9/format-docstring" in precommit
        assert "id: format-docstring" in precommit
        assert "[testenv:pre-commit]" in tox_config
        assert "pre-commit run --all-files --show-diff-on-failure" in tox_config
        assert "[testenv:repo-checks]" in tox_config
        assert "pre-commit run --hook-stage manual --all-files --show-diff-on-failure" in tox_config
        assert tox_config.count("    PRE_COMMIT_HOME") == 2
        assert tox_config.count("    TMPDIR") == 2
        assert precommit.startswith("default_stages: [pre-commit]\n")
        assert "stages: [pre-commit, manual]" in precommit

        precommit_config = yaml.safe_load(precommit)
        manual_hook_ids: set[str] = set()
        default_stage_hook_ids: set[str] = set()
        for repository in precommit_config["repos"]:
            for hook in repository["hooks"]:
                hook_id = hook["id"]
                stages = hook.get("stages")
                if stages is None:
                    default_stage_hook_ids.add(hook_id)
                elif "manual" in stages:
                    manual_hook_ids.add(hook_id)

        assert {
            "check-added-large-files",
            "check-case-conflict",
            "check-illegal-windows-names",
            "check-json",
            "check-merge-conflict",
            "check-toml",
            "check-yaml",
            "debug-statements",
            "detect-private-key",
            "end-of-file-fixer",
            "mixed-line-ending",
            "name-tests-test",
            "trailing-whitespace",
        } <= manual_hook_ids
        assert {
            "format-docstring",
            "ruff-check",
            "ruff-format",
        } <= default_stage_hook_ids
        assert not ({"format-docstring", "ruff-check", "ruff-format"} & manual_hook_ids)
        if answers["use_notebooks"]:
            assert {"nbstripout", "format-docstring-jupyter"} <= default_stage_hook_ids
            assert not ({"nbstripout", "format-docstring-jupyter"} & manual_hook_ids)
    else:
        assert "[testenv:pre-commit]" not in tox_config
        assert "[testenv:repo-checks]" not in tox_config

    if answers["use_dvc"]:
        assert answers["project_kind"] == "data_science"
        assert (destination / ".dvc/config").is_file()
        assert (destination / ".dvc/.gitignore").is_file()
        assert (destination / ".dvcignore").is_file()
        assert (destination / "dvc.yaml").is_file()
        assert "dvc" in pyproject["dependency-groups"]
        assert has_dependency(pyproject["dependency-groups"]["dvc"], "dvc")
        assert "[testenv:dvc]" in tox_config
        assert "dvc status" in tox_config
    else:
        assert not (destination / ".dvc").exists()
        assert not (destination / ".dvcignore").exists()
        assert not (destination / "dvc.yaml").exists()
        assert "dvc" not in pyproject["dependency-groups"]
        assert "[testenv:dvc]" not in tox_config

    if answers["use_docs"]:
        conf = (destination / "docs/source/conf.py").read_text()
        assert (destination / "docs/source/conf.py").is_file()
        assert f"napoleon_google_docstring = {answers['docstring_style'] == 'google'}" in conf
        assert f"napoleon_numpy_docstring = {answers['docstring_style'] == 'numpy'}" in conf
        assert "[testenv:docs]" in tox_config
        assert "[testenv:docs-html]" not in tox_config
        assert "[testenv:docs-coverage]" not in tox_config
        assert "python scripts/build_docs.py {posargs:all}" in tox_config
        assert "build the selected documentation target" in tox_config
        docs_script = (destination / "scripts/build_docs.py").read_text()
        assert 'choices=("all", "html", "coverage", "clean")' in docs_script
        assert '"-b",' in docs_script
        assert '"-d",' in docs_script
        assert "check_api_coverage()" in docs_script
        assert 'html_report = coverage_directory / "index.html"' in docs_script
        assert "html.escape(report_text)" in docs_script
        assert "Sphinx API documentation coverage is incomplete." in docs_script
        assert "failures: list[str] = []" in docs_script
        assert docs_script.index('build("coverage")') < docs_script.rindex('build("html")')
        assert 'environment["PROJECT_DOCS_BUILDER"] = builder' in docs_script
        assert 'documentation_builder == "coverage"' in conf
        assert '"diagrams/**"' in conf

        makefile = (destination / "docs/Makefile").read_text()
        make_bat = (destination / "docs/make.bat").read_text()
        assert "../scripts/build_docs.py $@" in makefile
        assert "%PYTHON% ..\\scripts\\build_docs.py %TARGET%" in make_bat
        assert 'IF /I "%TARGET%" == "clean" GOTO :build' in make_bat
        assert "ENDLOCAL & EXIT /B %STATUS%" in make_bat
        assert "coverage_show_missing_items = True" in conf
        assert "coverage_statistics_to_stdout = True" in conf
        assert 'templates_path = ["_templates"]' in conf
        assert "autodoc_default_options" not in conf
        assert 'suppress_warnings = ["toc.excluded"]' in conf
        assert "source_suffix" not in conf
        assert "project_metadata = load_project_metadata()" in conf
        assert 'project = str(project_metadata["name"])' in conf
        assert "author = format_authors(project_metadata)" in conf
        assert 'project_license = str(project_metadata.get("license", ""))' in conf
        assert "release = metadata.version(project)" in conf
        assert '"sphinx.ext.duration"' in conf
        assert (destination / "docs/source/readme.md").is_file()
        documentation_guide = (destination / "docs/README.md").read_text(encoding="utf-8")
        assert "# Documentation contributor guide" in documentation_guide
        assert "uv run --locked tox run -e docs -- html" in documentation_guide
        assert not documentation_guide.endswith("\n\n")
        assert "repository-facing by default" in documentation_guide
        assert not (destination / "docs/source/documentation-guide.md").exists()
        generated_readme = (destination / "README.md").read_text(encoding="utf-8")
        contributing = (destination / "CONTRIBUTING.md").read_text(encoding="utf-8")
        maintaining = (destination / "MAINTAINING.md").read_text(encoding="utf-8")
        assert "| `docs/README.md` | Documentation authors | Pages, API reference" in generated_readme
        assert "documentation-author workflow is in `docs/README.md`" in contributing
        assert "Documentation authoring is documented in `docs/README.md`" in maintaining
        assert "[`docs/README.md`](docs/README.md)" not in generated_readme
        documentation_index = (destination / "docs/source/index.md").read_text(encoding="utf-8")
        assert "readme\ncommand-reference\napi" in documentation_index
        readme_document = (destination / "docs/source/readme.md").read_text(encoding="utf-8")
        assert "```{include} ../../README.md" in readme_document
        assert ':start-after: "# Example Project"' in readme_document

        autosummary_templates = destination / "docs/source/_templates/autosummary"
        module_template = (autosummary_templates / "module.rst").read_text(encoding="utf-8")
        class_template = (autosummary_templates / "class.rst").read_text(encoding="utf-8")
        assert "{{ fullname | escape | underline }}" in module_template
        assert "Module Attributes" in module_template
        assert "Functions" in module_template
        assert "Classes" in module_template
        assert "Exceptions" in module_template
        assert "Modules" in module_template
        assert module_template.count(":toctree:") == 5
        assert ":recursive:" in module_template
        assert "{{ fullname | escape | underline }}" in class_template
        assert ":members:" in class_template
        assert ":inherited-members:" in class_template
        assert ":show-inheritance:" in class_template
        assert ":special-members: __init__" in class_template
        assert "Methods" in class_template
        assert "Attributes" in class_template
        api_reference = (destination / "docs/source/api.rst").read_text(encoding="utf-8")
        assert ":recursive:" in api_reference
        if answers["use_notebooks"]:
            assert 'nb_execution_mode = "off"' in conf
            assert '"myst_nb"' in conf
            assert has_dependency(pyproject["dependency-groups"]["docs"], "myst-nb")
            assert not has_dependency(pyproject["dependency-groups"]["docs"], "nbsphinx")
            assert "nbgallery" not in (destination / "docs/source/notebooks/index.rst").read_text(encoding="utf-8")

        generated_gitignore = (destination / ".gitignore").read_text()
        assert "reports/\n" not in generated_gitignore
        assert ".coverage.*" in generated_gitignore
        assert "pytest-of-*/" in generated_gitignore
        assert "reports/coverage/" in generated_gitignore
        assert "reports/pytest/" in generated_gitignore
        assert "reports/sphinx/" in generated_gitignore
        if answers["use_example_gallery"]:
            assert "docs/source/auto_examples/" in generated_gitignore
            assert "docs/source/sg_execution_times.rst" in generated_gitignore
            assert 'rmtree(SOURCE / "auto_examples", ignore_errors=True)' in docs_script
            assert '(SOURCE / "sg_execution_times.rst").unlink(missing_ok=True)' in docs_script
        clean_script = (destination / "scripts/clean.py").read_text()
        assert 'ROOT.glob(".coverage.*")' in clean_script
        assert 'ROOT.glob("pytest-of-*")' in clean_script
        assert 'ROOT / "reports",' not in clean_script
        assert 'ROOT / "reports" / "coverage"' in clean_script
        assert 'ROOT / "reports" / "pytest"' in clean_script
        assert 'ROOT / "reports" / "sphinx"' in clean_script
        if answers["use_example_gallery"]:
            assert 'ROOT / "docs" / "source" / "auto_examples"' in clean_script
            assert 'ROOT / "docs" / "source" / "sg_execution_times.rst"' in clean_script

        if answers["use_uml"]:
            assert "[testenv:uml]" in tox_config
            assert "python scripts/generate_uml.py" in tox_config
            assert (destination / "scripts/generate_uml.py").is_file()
            docs_dependencies = pyproject["dependency-groups"]["docs"]
            assert has_dependency(docs_dependencies, "sphinxcontrib-mermaid")
            assert '"sphinxcontrib.mermaid"' in conf
            assert 'mermaid_output_format = "raw"' in conf
            assert '"sphinx.ext.graphviz"' not in conf
            uml_script = (destination / "scripts/generate_uml.py").read_text(encoding="utf-8")
            assert '"mmd"' in uml_script
            diagrams = (destination / "docs/source/diagrams/index.rst").read_text(encoding="utf-8")
            assert ".. mermaid:: packages.mmd" in diagrams
            assert ".. mermaid:: classes.mmd" in diagrams
        else:
            assert "[testenv:uml]" not in tox_config
            assert not (destination / "scripts/generate_uml.py").exists()
    else:
        assert not (destination / "docs").exists()
        assert not (destination / "docs/README.md").exists()
        assert "[testenv:docs]" not in tox_config
        assert "[testenv:docs-html]" not in tox_config
        assert "[testenv:docs-coverage]" not in tox_config
        assert "[testenv:uml]" not in tox_config

    if answers["use_notebooks"]:
        notebook_path = destination / "notebooks/example.ipynb"
        assert notebook_path.is_file()
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        assert [cell["id"] for cell in notebook["cells"]] == ["0", "1"]
        assert (destination / "scripts/check_notebooks.py").is_file()
        assert "[testenv:notebooks]" in tox_config
        groups = pyproject["dependency-groups"]
        assert "notebooks" in groups
        assert any("jupyterlab" in dependency for dependency in groups["notebooks"])

        if answers["use_precommit"]:
            precommit = (destination / ".pre-commit-config.yaml").read_text()
            assert "kynan/nbstripout" in precommit
            assert "^notebooks/.*\\.ipynb$" in precommit
            assert "id: format-docstring-jupyter" in precommit

        ruff_ignores = pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]
        assert "notebooks/**/*.ipynb" in ruff_ignores
    else:
        assert not (destination / "notebooks").exists()
        assert not (destination / "scripts/check_notebooks.py").exists()
        assert "[testenv:notebooks]" not in tox_config
        assert "notebooks" not in pyproject["dependency-groups"]
        if answers["use_precommit"]:
            precommit = (destination / ".pre-commit-config.yaml").read_text()
            assert "kynan/nbstripout" not in precommit

    if answers["project_kind"] == "data_science":
        assert "ICN" in pyproject["tool"]["ruff"]["lint"]["select"]
        assert "NPY" in pyproject["tool"]["ruff"]["lint"]["select"]
        assert (destination / "data/raw/.gitkeep").is_file()
        assert (destination / "tests/data/README.md").is_file()
        assert has_dependency(test_dependencies, "pytest-datadir")
        assert has_dependency(pytest_options["required_plugins"], "pytest-datadir")
    else:
        assert "ICN" not in pyproject["tool"]["ruff"]["lint"]["select"]
        assert "NPY" not in pyproject["tool"]["ruff"]["lint"]["select"]
        assert not (destination / "data").exists()
        assert not (destination / "tests/data").exists()
        assert not has_dependency(test_dependencies, "pytest-datadir")

    if answers["use_example_gallery"]:
        assert (destination / "examples/GALLERY_HEADER.rst").is_file()
        assert (destination / "examples/plot_quadratic.py").is_file()
        docs_dependencies = pyproject["dependency-groups"]["docs"]
        assert has_dependency(docs_dependencies, "sphinx-gallery")
        assert has_dependency(docs_dependencies, "matplotlib")
        conf = (destination / "docs/source/conf.py").read_text()
        assert "sphinx_gallery.gen_gallery" in conf
        assert "../../examples" in conf
        assert "auto_examples/*.ipynb" in conf
        assert "auto_examples/**/*.ipynb" in conf
        assert "auto_examples/*.py" in conf
        assert "auto_examples/**/*.py" in conf
        gallery_example = (destination / "examples/plot_quadratic.py").read_text(encoding="utf-8")
        assert pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]["examples/**/*.py"] == ["D205", "D415"]
        assert "# no-format-docstring" in gallery_example
        assert "Plot a quadratic function\n=========================" in gallery_example
    else:
        assert not (destination / "examples").exists()

    ci_provider = answers["ci_provider"]
    github_ci = destination / ".github/workflows/ci.yml"
    github_renovate_ci = destination / ".github/workflows/renovate.yml"
    gitlab_ci = destination / ".gitlab-ci.yml"
    bitbucket_ci = destination / "bitbucket-pipelines.yml"

    if ci_provider == "github":
        assert github_ci.is_file()
        assert github_renovate_ci.is_file()
        assert not gitlab_ci.exists()
        assert not bitbucket_ci.exists()
        ci_text = github_ci.read_text()
        renovate_ci_text = github_renovate_ci.read_text(encoding="utf-8")
        yaml.safe_load(ci_text)
        yaml.safe_load(renovate_ci_text)
        assert "tox run -e lock" in ci_text
        assert "tox run -e lint" in ci_text
        assert "tox run -e package-check" in ci_text
        assert "tox run -e build" not in ci_text
        assert "cancel-in-progress: true" in ci_text
        assert "actions/checkout@v7" in ci_text
        assert "astral-sh/setup-uv@v9" in ci_text
        assert "reports/pytest/" in ci_text
        assert "reports/coverage/" in ci_text
        assert "if-no-files-found: error" in ci_text
        if answers["use_docs"]:
            assert "name: documentation" in ci_text
            assert "path: reports/sphinx/" in ci_text
        assert ("tox run -e repo-checks" in ci_text) is bool(answers["use_precommit"])
        assert "tox run -e pre-commit" not in ci_text
        assert "uv run pytest" not in ci_text
        assert ("tox run -e dvc" in ci_text) is bool(answers["use_dvc"])
        assert "name: Renovate" in renovate_ci_text
        assert 'cron: "0 5 * * *"' in renovate_ci_text
        assert "workflow_dispatch:" in renovate_ci_text
        assert "renovatebot/github-action" in renovate_ci_text
        assert "secrets.RENOVATE_TOKEN" in renovate_ci_text
    elif ci_provider == "gitlab":
        assert gitlab_ci.is_file()
        assert not github_ci.exists()
        assert not github_renovate_ci.exists()
        assert not bitbucket_ci.exists()
        ci_text = gitlab_ci.read_text()
        yaml.safe_load(ci_text)
        assert "tox run -e lock" in ci_text
        assert "tox run -e lint" in ci_text
        assert "tox run -e package-check" in ci_text
        assert "tox run -e build" not in ci_text
        assert "on_new_commit: interruptible" in ci_text
        assert "interruptible: true" in ci_text
        assert "renovate:" in ci_text
        assert "npx --yes renovate --autodiscover --onboarding-branch=renovate/init" in ci_text
        assert 'if: $CI_PIPELINE_SOURCE == "schedule"' in ci_text
        assert ("tox run -e repo-checks" in ci_text) is bool(answers["use_precommit"])
        assert "tox run -e pre-commit" not in ci_text
        assert ("tox run -e dvc" in ci_text) is bool(answers["use_dvc"])
    elif ci_provider == "bitbucket":
        assert bitbucket_ci.is_file()
        assert not github_ci.exists()
        assert not github_renovate_ci.exists()
        assert not gitlab_ci.exists()
        ci_text = bitbucket_ci.read_text()
        yaml.safe_load(ci_text)
        assert "tox run -e lock" in ci_text
        assert "tox run -e lint" in ci_text
        assert "tox run -e package-check" in ci_text
        assert "tox run -e build" not in ci_text
        assert "cancel-in-progress: true" not in ci_text
        assert "on_new_commit: interruptible" not in ci_text
        assert ("tox run -e repo-checks" in ci_text) is bool(answers["use_precommit"])
        assert "tox run -e pre-commit" not in ci_text
        assert ("tox run -e dvc" in ci_text) is bool(answers["use_dvc"])
    else:
        assert not github_ci.exists()
        assert not github_renovate_ci.exists()
        assert not gitlab_ci.exists()
        assert not bitbucket_ci.exists()

    if ci_provider != "none":
        assert "graphviz" not in ci_text.lower()

    run("python", "-m", "compileall", "-q", "src", "tests", "scripts", cwd=destination)

    if os.environ.get("RUN_GENERATED_BUILDS") == "1":
        run("git", "init", cwd=destination)
        run("git", "config", "user.name", "Template CI", cwd=destination)
        run("git", "config", "user.email", "template@example.com", cwd=destination)
        run("git", "add", ".", cwd=destination)
        run("git", "commit", "-m", "Initial project", cwd=destination)
        run("git", "tag", "v0.0.1", cwd=destination)
        run("uv", "build", cwd=destination)


def test_normal_project_starter_tests_meet_coverage_threshold(tmp_path: Path) -> None:
    """Keep the generated starter suite above its configured coverage gate."""
    destination = tmp_path / "normal-project"
    render_generated_project(destination, NORMAL_PROJECT_REGRESSION_OVERRIDES)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(destination / "src")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-c",
            os.devnull,
            "--cov=example_project",
            "--cov-branch",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            str(destination / "tests"),
        ],
        cwd=destination,
        env=environment,
        check=True,
    )


@pytest.mark.skipif(
    os.environ.get("RUN_NORMAL_PROJECT") != "1",
    reason="set RUN_NORMAL_PROJECT=1 to run a normal generated project's complete initialisation lifecycle",
)
def test_normal_project_complete_lifecycle(tmp_path: Path) -> None:
    """Render and bootstrap the option combination from the coverage regression report."""
    destination = tmp_path / "normal-project"
    render_generated_project(destination, NORMAL_PROJECT_REGRESSION_OVERRIDES)
    precommit_home = tmp_path / "pre-commit-home"
    temporary_directory = tmp_path / "tmp"
    precommit_home.mkdir()
    temporary_directory.mkdir()
    environment = os.environ.copy()
    environment["PRE_COMMIT_HOME"] = str(precommit_home)
    environment["TMPDIR"] = str(temporary_directory)

    subprocess.run(
        [
            "uv",
            "run",
            "scripts/init_project.py",
            "--git-name",
            "Template CI",
            "--git-email",
            "template@example.com",
        ],
        cwd=destination,
        env=environment,
        check=True,
    )

    subprocess.run(
        ["uv", "run", "--locked", "tox"],
        cwd=destination,
        env=environment,
        check=True,
    )

    assert command_output("git", "tag", "--points-at", "HEAD", cwd=destination).splitlines() == ["v0.0.1"]
    assert command_output("git", "status", "--short", cwd=destination) == ""
    assert not list(destination.glob("setup_*.log"))
