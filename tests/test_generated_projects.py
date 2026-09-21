from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest
import yaml
from _render import (
    BASE_ANSWERS,
    NORMAL_PROJECT_REGRESSION_OVERRIDES,
    TEMPLATE_ROOT,
    case_id_for,
    generated_documentation,
    has_dependency,
    load_toml,
    render_generated_project,
)
from copier import run_copy, run_update
from jinja2 import Environment

MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MYST_INCLUDE = re.compile(r"^```\{include\}\s+(.+?)\s*$", re.MULTILINE)
SCRIPT_REFERENCE = re.compile(r"\b(scripts/[a-zA-Z0-9_-]+\.py)\b")
TOCTREE = re.compile(r"```\{toctree\}\s*\n(.*?)```", re.DOTALL)
TOX_ENVIRONMENT_REFERENCE = re.compile(r"\btox run -e ([a-zA-Z0-9_-]+)\b")
CI_TOX_ENV_LITERAL = re.compile(r"tox run -e ([a-z0-9-]+)")
CI_GITHUB_MATRIX_ENV = re.compile(r"tox-env:\s*\"([a-z0-9-]+)\"")
EXTERNAL_LINK_PREFIXES = ("http://", "https://", "mailto:")


def run(*command: str, cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def command_output(*command: str, cwd: Path) -> str:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True).stdout


# --- Template-level contracts (no rendering required) -----------------------


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

    assert script.startswith('# /// script\n# requires-python = ">=3.11"\n# dependencies = ["pyyaml>=6"]\n# ///')
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
    """The default python_versions list is derived from the copier.yml ``minimum_python_version`` choices.

    ``python_versions`` is a Jinja2 template (not plain YAML), so we render it
    with each allowed minimum and check that it returns the supported list from
    that minimum up to the maximum supported choice. This keeps a single source
    of truth (``copier.yml``) and picks up newly-supported Pythons without a
    table change here.
    """
    copier_config = yaml.safe_load((TEMPLATE_ROOT / "copier.yml").read_text())
    supported = list(copier_config["minimum_python_version"]["choices"].values())
    expected = {minimum: [v for v in supported if _version_key(v) >= _version_key(minimum)] for minimum in supported}
    default_template = Environment().from_string(copier_config["python_versions"]["default"])

    for minimum_version, expected_versions in expected.items():
        rendered = default_template.render(minimum_python_version=minimum_version)
        assert yaml.safe_load(rendered) == expected_versions, (minimum_version, rendered)


def _version_key(version: str) -> tuple[int, int]:
    major, minor = version.split(".", maxsplit=1)
    return int(major), int(minor)


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


# --- Generated-project contracts --------------------------------------------
# These tests share one render per case (the `rendered` fixture in `conftest.py`).
# Each test focuses on one concern so that adding a feature touches a small,
# well-named test rather than a monolith.


def test_generated_documentation_references_are_valid(destination: Path, answers: dict[str, object]) -> None:
    """Validate links, commands, includes, and navigation in every rendered variant."""
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


def test_generated_sphinx_command_reference_matches_selected_features(
    destination: Path,
    answers: dict[str, object],
) -> None:
    """Document every rendered Tox task without advertising unavailable features."""
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


def test_pyproject_metadata_and_dependencies(destination: Path) -> None:
    pyproject = load_toml(destination)
    assert pyproject["project"]["name"] == "example-project"
    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["project"]["urls"] == {
        "Homepage": "https://example-project.example",
        "Documentation": "https://docs.example-project.example",
        "Repository": "https://github.com/example/example-project",
        "Issues": "https://github.com/example/example-project/issues",
        "Changelog": "https://github.com/example/example-project/blob/main/CHANGELOG.md",
    }

    groups = pyproject["dependency-groups"]
    assert has_dependency(groups["lint"], "format-docstring")
    assert has_dependency(groups["lint"], "pytest")
    assert has_dependency(groups["package-check"], "check-wheel-contents")
    assert has_dependency(groups["package-check"], "twine")
    assert has_dependency(groups["test"], "pytest-reportlog")
    assert has_dependency(groups["dev"], "pytest-sugar")
    assert has_dependency(groups["dev"], "tox")
    assert has_dependency(groups["dev"], "tox-uv")


def test_pyproject_tool_configuration(destination: Path, answers: dict[str, object]) -> None:
    pyproject = load_toml(destination)
    assert pyproject["tool"]["format_docstring"]["docstring_style"] == answers["docstring_style"]
    assert pyproject["tool"]["ruff"]["lint"]["pydocstyle"]["convention"] == answers["docstring_style"]
    assert pyproject["tool"]["ruff"]["line-length"] == 121
    assert pyproject["tool"]["ruff"]["force-exclude"] is True
    assert pyproject["tool"]["format_docstring"]["line_length"] == 121
    assert pyproject["tool"]["ruff"]["format"]["docstring-code-format"] is True
    assert pyproject["tool"]["ruff"]["format"]["docstring-code-line-length"] == "dynamic"
    assert "G" in pyproject["tool"]["ruff"]["lint"]["select"]
    assert "LOG" in pyproject["tool"]["ruff"]["lint"]["select"]

    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    assert has_dependency(pytest_options["required_plugins"], "pytest-reportlog")
    assert all(">=" in requirement for requirement in pytest_options["required_plugins"])
    assert "--report-log=reports/pytest/report.jsonl" in pytest_options["addopts"]
    assert "--cov=example_project" in pytest_options["addopts"]
    assert "--cov-report=html:reports/coverage/html" in pytest_options["addopts"]
    assert "--cov-report=xml:reports/coverage/coverage.xml" in pytest_options["addopts"]
    assert "--cov-report=json:reports/coverage/coverage.json" in pytest_options["addopts"]
    assert "--cov-branch" not in pytest_options["addopts"]
    assert pytest_options["log_cli"] is False
    assert pytest_options["log_file"] == "reports/pytest/logs/pytest.log"


def test_source_and_layout_files(destination: Path) -> None:
    assert (destination / "src/example_project/__init__.py").is_file()
    assert (destination / "tests/test_main.py").is_file()
    assert (destination / "tox.ini").is_file()
    assert (destination / "CONTRIBUTING.md").is_file()
    assert (destination / "MAINTAINING.md").is_file()


def test_renovate_and_editorconfig(destination: Path) -> None:
    renovate_config = json.loads((destination / "renovate.json").read_text(encoding="utf-8"))
    assert "enabledManagers" not in renovate_config
    assert renovate_config["lockFileMaintenance"]["enabled"] is True
    routine_updates = renovate_config["packageRules"][0]
    assert "matchManagers" not in routine_updates
    assert routine_updates["matchUpdateTypes"] == ["minor", "patch", "pin", "digest"]

    editorconfig = (destination / ".editorconfig").read_text()
    assert "[Makefile]" in editorconfig
    assert "indent_style = tab" in editorconfig


def test_generated_readme(destination: Path, answers: dict[str, object]) -> None:
    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert len(readme.splitlines()) < 150
    assert not readme.endswith("\n\n")
    assert "uv sync --locked" in readme
    assert "| `CONTRIBUTING.md` | Contributors | Environment setup" in readme
    assert "| `MAINTAINING.md` | Maintainers | One-time bootstrap" in readme
    assert "uv run scripts/init_project.py" not in readme

    if answers["use_docs"]:
        assert "| `docs/README.md` | Documentation authors | Pages, API reference" in readme
        assert "[`docs/README.md`](docs/README.md)" not in readme
    else:
        assert "docs/README.md" not in readme


def test_generated_contributing(destination: Path, answers: dict[str, object]) -> None:
    contributing = (destination / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert not contributing.endswith("\n\n")
    assert "# Contributing to Example Project" in contributing
    assert "Tox is the preferred project-level task interface" in contributing
    assert "| Task | Preferred Tox command | Direct command |" in contributing
    assert "uv run --locked tox run -e lint" in contributing
    assert "uv run --locked --group lint ruff check ." in contributing
    assert "build and test the installed wheel" in contributing

    assert ("tox run -e pre-commit" in contributing) is bool(answers["use_precommit"])
    assert ("tox run -e notebooks" in contributing) is bool(answers["use_notebooks"])
    assert ("tox run -e docs -- html" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e docs -- coverage" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e docs -- clean" in contributing) is bool(answers["use_docs"])
    assert ("tox run -e dvc" in contributing) is bool(answers["project_kind"] == "data_science" and answers["use_dvc"])
    assert ("## Propose changes" in contributing) is bool(answers["has_other_contributors"])
    assert ("## Report bugs" in contributing) is bool(answers["has_other_contributors"])

    if answers["use_docs"]:
        assert "documentation-author workflow is in `docs/README.md`" in contributing
    if answers["ci_provider"] == "bitbucket":
        assert "Bitbucket does not consume repository-defined issue templates" in contributing


def test_generated_maintaining(destination: Path, answers: dict[str, object]) -> None:
    maintaining = (destination / "MAINTAINING.md").read_text(encoding="utf-8")
    assert not maintaining.endswith("\n\n")
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
    assert ("## Collaboration configuration" in maintaining) is bool(answers["has_other_contributors"])

    if answers["use_docs"]:
        assert "Documentation authoring is documented in `docs/README.md`" in maintaining


def test_guide_external_links(destination: Path, answers: dict[str, object]) -> None:
    project_guides = "\n".join(
        (destination / name).read_text(encoding="utf-8") for name in ("README.md", "CONTRIBUTING.md", "MAINTAINING.md")
    )
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


def test_collaboration_files(destination: Path, answers: dict[str, object]) -> None:
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
    if not answers["has_other_contributors"]:
        return

    assert str(answers["code_owners"]) in (destination / collaboration_paths[str(answers["ci_provider"])][0]).read_text(
        encoding="utf-8"
    )
    assert "author@example.com" in code_of_conduct.read_text(encoding="utf-8")


def test_tox_always_on_environments(destination: Path) -> None:
    tox_config = (destination / "tox.ini").read_text()
    assert "[testenv:lock]" in tox_config
    assert "uv lock --check" in tox_config
    assert "[testenv:lint]" in tox_config
    assert "[testenv:package-check]" in tox_config
    assert "python scripts/check_package.py" in tox_config
    assert "[testenv:build]" in tox_config
    assert "[testenv:clean]" in tox_config
    assert "labels = test" in tox_config
    assert "uv build" in tox_config


def test_scripts_present(destination: Path) -> None:
    package_check_script = (destination / "scripts/check_package.py").read_text(encoding="utf-8")
    assert (destination / "scripts/check_package.py").is_file()
    assert "distributions = [*source_distributions, *wheels]" in package_check_script
    assert (destination / "scripts/init_project.py").is_file()
    assert not (destination / "scripts/setup_project.py").exists()


def test_no_template_leakage(destination: Path) -> None:
    assert not list(destination.rglob("*.jinja"))

    autosummary_template_root = destination / "docs/source/_templates/autosummary"
    rendered_text = "\n".join(
        path.read_text(errors="ignore")
        for path in destination.rglob("*")
        if path.is_file() and path.stat().st_size < 1_000_000 and not path.is_relative_to(autosummary_template_root)
    )
    assert "{{ package_name }}" not in rendered_text
    assert "{% if" not in rendered_text


def test_main_module_docstring_style(destination: Path, answers: dict[str, object]) -> None:
    main_module = (destination / "src/example_project/main.py").read_text()
    if answers["docstring_style"] == "google":
        assert "    Args:" in main_module
        assert "    Parameters\n    ----------" not in main_module
    else:
        assert "    Parameters\n    ----------" in main_module
        assert "    Args:" not in main_module


def test_build_backend(destination: Path, answers: dict[str, object]) -> None:
    if answers["build_backend"] != "setuptools":
        return
    pyproject = load_toml(destination)
    assert pyproject["build-system"]["requires"] == ["setuptools>=80", "setuptools-scm[simple]>=10.2"]
    assert "setuptools" not in pyproject.get("tool", {})
    assert "setuptools_scm" not in pyproject.get("tool", {})


def test_precommit_configuration(destination: Path, answers: dict[str, object]) -> None:
    tox_config = (destination / "tox.ini").read_text()
    if not answers["use_precommit"]:
        assert "[testenv:pre-commit]" not in tox_config
        assert "[testenv:repo-checks]" not in tox_config
        return

    precommit = (destination / ".pre-commit-config.yaml").read_text()
    assert "jsh9/format-docstring" in precommit
    assert "id: format-docstring" in precommit
    assert precommit.startswith("default_stages: [pre-commit]\n")
    assert "stages: [pre-commit, manual]" in precommit
    assert "[testenv:pre-commit]" in tox_config
    assert "pre-commit run --all-files --show-diff-on-failure" in tox_config
    assert "[testenv:repo-checks]" in tox_config
    assert "pre-commit run --hook-stage manual --all-files --show-diff-on-failure" in tox_config
    assert tox_config.count("    PRE_COMMIT_HOME") == 2
    assert tox_config.count("    TMPDIR") == 2

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
    assert {"format-docstring", "ruff-check", "ruff-format"} <= default_stage_hook_ids
    assert not ({"format-docstring", "ruff-check", "ruff-format"} & manual_hook_ids)
    if answers["use_notebooks"]:
        assert {"nbstripout", "format-docstring-jupyter"} <= default_stage_hook_ids
        assert not ({"nbstripout", "format-docstring-jupyter"} & manual_hook_ids)


def test_dvc_integration(destination: Path, answers: dict[str, object]) -> None:
    tox_config = (destination / "tox.ini").read_text()
    pyproject = load_toml(destination)
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


def test_documentation_outputs(destination: Path, answers: dict[str, object]) -> None:
    if not answers["use_docs"]:
        assert not (destination / "docs").exists()
        assert not (destination / "docs/README.md").exists()
        return

    tox_config = (destination / "tox.ini").read_text()
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
    assert '"-d",' in docs_script
    assert "check_api_coverage()" in docs_script
    assert 'build("coverage")' in docs_script

    makefile = (destination / "docs/Makefile").read_text()
    make_bat = (destination / "docs/make.bat").read_text()
    assert "../scripts/build_docs.py $@" in makefile
    assert "%PYTHON% ..\\scripts\\build_docs.py %TARGET%" in make_bat
    assert 'IF /I "%TARGET%" == "clean" GOTO :build' in make_bat

    assert "coverage_show_missing_items = True" in conf
    assert "coverage_statistics_to_stdout = True" in conf
    assert 'templates_path = ["_templates"]' in conf
    assert "autodoc_default_options" not in conf
    assert 'suppress_warnings = ["toc.excluded"]' in conf
    assert "source_suffix" not in conf

    assert (destination / "docs/source/readme.md").is_file()
    documentation_guide = (destination / "docs/README.md").read_text(encoding="utf-8")
    assert "# Documentation contributor guide" in documentation_guide
    assert "uv run --locked tox run -e docs -- html" in documentation_guide
    assert not documentation_guide.endswith("\n\n")
    assert "repository-facing by default" in documentation_guide
    assert not (destination / "docs/source/documentation-guide.md").exists()

    documentation_index = (destination / "docs/source/index.md").read_text(encoding="utf-8")
    assert "readme\ncommand-reference\napi" in documentation_index
    readme_document = (destination / "docs/source/readme.md").read_text(encoding="utf-8")
    assert "```{include} ../../README.md" in readme_document
    assert ':start-after: "# Example Project"' in readme_document

    generated_gitignore = (destination / ".gitignore").read_text()
    for line in (".coverage.*", "pytest-of-*/", "reports/coverage/", "reports/pytest/", "reports/sphinx/"):
        assert line in generated_gitignore


def test_uml_integration(destination: Path, answers: dict[str, object]) -> None:
    tox_config = (destination / "tox.ini").read_text() if answers["use_docs"] else ""
    if not (answers["use_docs"] and answers["use_uml"]):
        assert not (destination / "scripts/generate_uml.py").exists()
        if tox_config:
            assert "[testenv:uml]" not in tox_config
        return

    assert "[testenv:uml]" in tox_config
    assert "python scripts/generate_uml.py" in tox_config
    assert (destination / "scripts/generate_uml.py").is_file()

    conf = (destination / "docs/source/conf.py").read_text()
    pyproject = load_toml(destination)
    assert has_dependency(pyproject["dependency-groups"]["docs"], "sphinxcontrib-mermaid")
    assert '"sphinxcontrib.mermaid"' in conf
    assert 'mermaid_output_format = "raw"' in conf
    assert '"sphinx.ext.graphviz"' not in conf

    uml_script = (destination / "scripts/generate_uml.py").read_text(encoding="utf-8")
    assert '"mmd"' in uml_script
    diagrams = (destination / "docs/source/diagrams/index.rst").read_text(encoding="utf-8")
    assert ".. mermaid:: packages.mmd" in diagrams
    assert ".. mermaid:: classes.mmd" in diagrams


def test_notebooks_integration(destination: Path, answers: dict[str, object]) -> None:
    tox_config = (destination / "tox.ini").read_text()
    pyproject = load_toml(destination)
    if answers["use_notebooks"]:
        notebook_path = destination / "notebooks/example.ipynb"
        assert notebook_path.is_file()
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        assert [cell["id"] for cell in notebook["cells"]] == ["0", "1"]
        assert (destination / "scripts/check_notebooks.py").is_file()
        assert "[testenv:notebooks]" in tox_config
        assert "notebooks" in pyproject["dependency-groups"]
        assert any("jupyterlab" in dependency for dependency in pyproject["dependency-groups"]["notebooks"])
        assert pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]["notebooks/**/*.ipynb"]

        if answers["use_precommit"]:
            precommit = (destination / ".pre-commit-config.yaml").read_text()
            assert "kynan/nbstripout" in precommit
            assert "id: format-docstring-jupyter" in precommit
    else:
        assert not (destination / "notebooks").exists()
        assert not (destination / "scripts/check_notebooks.py").exists()
        assert "[testenv:notebooks]" not in tox_config
        assert "notebooks" not in pyproject["dependency-groups"]
        if answers["use_precommit"]:
            precommit = (destination / ".pre-commit-config.yaml").read_text()
            assert "kynan/nbstripout" not in precommit


def test_data_science_layout(destination: Path, answers: dict[str, object]) -> None:
    pyproject = load_toml(destination)
    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    if answers["project_kind"] == "data_science":
        assert "ICN" in pyproject["tool"]["ruff"]["lint"]["select"]
        assert "NPY" in pyproject["tool"]["ruff"]["lint"]["select"]
        assert (destination / "data/raw/.gitkeep").is_file()
        assert (destination / "tests/data/README.md").is_file()
        assert has_dependency(pyproject["dependency-groups"]["test"], "pytest-datadir")
        assert has_dependency(pytest_options["required_plugins"], "pytest-datadir")
    else:
        assert "ICN" not in pyproject["tool"]["ruff"]["lint"]["select"]
        assert "NPY" not in pyproject["tool"]["ruff"]["lint"]["select"]
        assert not (destination / "data").exists()
        assert not (destination / "tests/data").exists()
        assert not has_dependency(pyproject["dependency-groups"]["test"], "pytest-datadir")


def test_example_gallery(destination: Path, answers: dict[str, object]) -> None:
    if not answers["use_example_gallery"]:
        assert not (destination / "examples").exists()
        return

    pyproject = load_toml(destination)
    assert (destination / "examples/GALLERY_HEADER.rst").is_file()
    assert (destination / "examples/plot_quadratic.py").is_file()
    assert has_dependency(pyproject["dependency-groups"]["docs"], "sphinx-gallery")
    assert has_dependency(pyproject["dependency-groups"]["docs"], "matplotlib")
    assert pyproject["tool"]["ruff"]["lint"]["per-file-ignores"]["examples/**/*.py"] == ["D205", "D415"]

    gallery_example = (destination / "examples/plot_quadratic.py").read_text(encoding="utf-8")
    assert "# no-format-docstring" in gallery_example
    assert "Plot a quadratic function\n=========================" in gallery_example

    if answers["use_docs"]:
        conf = (destination / "docs/source/conf.py").read_text()
        assert "sphinx_gallery.gen_gallery" in conf
        assert "../../examples" in conf
    if (destination / "scripts/build_docs.py").exists():
        docs_script = (destination / "scripts/build_docs.py").read_text()
        assert 'rmtree(SOURCE / "auto_examples", ignore_errors=True)' in docs_script
        assert '(SOURCE / "sg_execution_times.rst").unlink(missing_ok=True)' in docs_script


def _extract_ci_tox_environments(ci_text: str) -> set[str]:
    """Return the Tox environments a rendered CI file invokes, across provider idioms."""
    environments = set(CI_TOX_ENV_LITERAL.findall(ci_text))
    # GitHub drives the per-version test envs through a matrix variable rather than a literal name.
    environments.update(CI_GITHUB_MATRIX_ENV.findall(ci_text))
    return environments


def _expected_ci_tox_environments(answers: dict[str, object]) -> set[str]:
    """Return the shared CI Tox contract for a feature selection (the set every provider must run)."""
    environments = {"lock", "lint", "package-check"}
    if answers["use_precommit"]:
        environments.add("repo-checks")
    for python_version in answers["python_versions"]:
        environments.add("py" + str(python_version).replace(".", ""))
    if answers["use_notebooks"]:
        environments.add("notebooks")
    if answers["project_kind"] == "data_science" and answers["use_dvc"]:
        environments.add("dvc")
    if answers["use_docs"]:
        environments.add("docs")
    return environments


def _ci_common(path: Path, answers: dict[str, object]) -> str:
    """Assert a rendered CI file runs exactly the shared Tox contract, no more and no less."""
    ci_text = path.read_text()
    yaml.safe_load(ci_text)
    extracted = _extract_ci_tox_environments(ci_text)
    expected = _expected_ci_tox_environments(answers)
    assert extracted == expected, (
        f"{path.name} invokes Tox envs {sorted(extracted)} but the shared CI contract for these "
        f"features is {sorted(expected)}. The three providers (GitHub, GitLab, Bitbucket) must all run the same set."
    )
    return ci_text


def test_ci_provider(destination: Path, answers: dict[str, object]) -> None:
    ci_provider = str(answers["ci_provider"])
    github_ci = destination / ".github/workflows/ci.yml"
    github_renovate_ci = destination / ".github/workflows/renovate.yml"
    gitlab_ci = destination / ".gitlab-ci.yml"
    bitbucket_ci = destination / "bitbucket-pipelines.yml"

    if ci_provider == "github":
        assert github_ci.is_file()
        assert github_renovate_ci.is_file()
        assert not gitlab_ci.exists()
        assert not bitbucket_ci.exists()
        ci_text = _ci_common(github_ci, answers)
        assert "cancel-in-progress: true" in ci_text
        assert "uv run pytest" not in ci_text
        if answers["use_docs"]:
            assert "name: documentation" in ci_text
            assert "path: reports/sphinx/" in ci_text
        # GitHub workflow uses actions; no version pinning is asserted so the
        # template does not have to update the test on every action bump.
        assert "actions/checkout" in ci_text
        assert "astral-sh/setup-uv" in ci_text

        renovate_ci_text = github_renovate_ci.read_text(encoding="utf-8")
        yaml.safe_load(renovate_ci_text)
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
        ci_text = _ci_common(gitlab_ci, answers)
        assert "on_new_commit: interruptible" in ci_text
        assert "interruptible: true" in ci_text
        assert "renovate:" in ci_text
        assert "npx --yes renovate --autodiscover --onboarding-branch=renovate/init" in ci_text
        assert 'if: $CI_PIPELINE_SOURCE == "schedule"' in ci_text
    elif ci_provider == "bitbucket":
        assert bitbucket_ci.is_file()
        assert not github_ci.exists()
        assert not github_renovate_ci.exists()
        assert not gitlab_ci.exists()
        _ci_common(bitbucket_ci, answers)
    else:
        assert not github_ci.exists()
        assert not github_renovate_ci.exists()
        assert not gitlab_ci.exists()
        assert not bitbucket_ci.exists()


def test_generated_project_compiles(destination: Path) -> None:
    run("python", "-m", "compileall", "-q", "src", "tests", "scripts", cwd=destination)


def test_structural_spec_matches_destination(
    rendered: tuple[Path, dict[str, object]], overrides: dict[str, object]
) -> None:
    """Spec-driven structural check.

    Regenerate the committed ``tests/specs/<case>.yaml`` files by running:

        EXPECTED_UPDATE=1 uv run --locked pytest

    Without that env var, drift between the committed spec and the rendered
    output is a failure with a readable set diff.
    """
    from expected import verify

    case_id = case_id_for(overrides)
    destination = rendered[0]
    verify(destination, case_id)


@pytest.mark.slow
def test_generated_project_build_package(destination: Path) -> None:
    """Slow: builds the rendered project end-to-end (needs a git repo + a tag)."""
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
            "--cov-fail-under=80",
            str(destination / "tests"),
        ],
        cwd=destination,
        env=environment,
        check=True,
    )


@pytest.mark.slow
@pytest.mark.skipif(
    os.environ.get("RUN_NORMAL_PROJECT") != "1", reason="set RUN_NORMAL_PROJECT=1 to run a full lifecycle"
)
def test_normal_project_complete_lifecycle(tmp_path: Path) -> None:
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
