"""Contracts for the template documentation set."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path
from urllib.parse import unquote

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
MARKDOWN_HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
NON_SLUG_CHARACTER = re.compile(r"[^\w\- ]")
MARKDOWN_FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:")
REQUIRED_GUIDES = (
    "index.md",
    "README.md",
    "getting-started.md",
    "template-options.md",
    "architecture.md",
    "command-reference.md",
    "ci-and-collaboration.md",
    "data-science.md",
    "maintenance.md",
    "updates-and-releases.md",
    "publishing.md",
    "troubleshooting.md",
)


def documentation_files() -> list[Path]:
    """Return authored template documentation files with local links."""
    return [ROOT / "README.md", *sorted(DOCS.glob("*.md"))]


def markdown_without_fenced_code(text: str) -> str:
    """Remove fenced examples while retaining prose line positions."""
    retained_lines: list[str] = []
    fence_character = ""
    fence_length = 0

    for line in text.splitlines():
        match = MARKDOWN_FENCE.match(line)
        if not fence_character and match:
            marker = match.group(1)
            fence_character = marker[0]
            fence_length = len(marker)
            retained_lines.append("")
        elif fence_character and match and match.group(1)[0] == fence_character and len(match.group(1)) >= fence_length:
            fence_character = ""
            fence_length = 0
            retained_lines.append("")
        elif fence_character:
            retained_lines.append("")
        else:
            retained_lines.append(line)

    return "\n".join(retained_lines)


def markdown_heading_slugs(document: Path) -> set[str]:
    """Return GitHub-style heading slugs from a Markdown document."""
    slugs: set[str] = set()
    text = markdown_without_fenced_code(document.read_text(encoding="utf-8"))
    for _, raw_heading in MARKDOWN_HEADING.findall(text):
        heading = raw_heading.strip().lower().replace("`", "")
        slugs.add(NON_SLUG_CHARACTER.sub("", heading).replace(" ", "-"))
    return slugs


def test_documentation_home_indexes_every_guide() -> None:
    """Require one discoverable documentation entry point."""
    documentation_home = (DOCS / "README.md").read_text(encoding="utf-8")

    for guide in REQUIRED_GUIDES:
        assert (DOCS / guide).is_file()
        if guide != "README.md":
            assert f"({guide})" in documentation_home


def test_documentation_guides_have_one_title_and_an_introduction() -> None:
    """Keep every guide independently understandable when opened directly."""
    for guide in sorted(DOCS.glob("*.md")):
        text = markdown_without_fenced_code(guide.read_text(encoding="utf-8"))
        lines = text.splitlines()
        titles = [line for line in lines if line.startswith("# ")]
        first_section = next((index for index, line in enumerate(lines) if line.startswith("## ")), len(lines))
        introduction = "\n".join(lines[1:first_section]).strip()

        assert len(titles) == 1, guide.relative_to(ROOT)
        assert lines[0] == titles[0], guide.relative_to(ROOT)
        assert introduction, guide.relative_to(ROOT)


def test_every_copier_question_is_documented() -> None:
    """Keep the answer reference synchronized with copier.yml."""
    copier_config = yaml.safe_load((ROOT / "copier.yml").read_text(encoding="utf-8"))
    option_reference = (DOCS / "template-options.md").read_text(encoding="utf-8")
    questions = {
        key
        for key, value in copier_config.items()
        if not key.startswith("_") and isinstance(value, dict) and "type" in value
    }

    assert questions
    for question in questions:
        assert f"`{question}`" in option_reference


def test_relative_documentation_links_resolve() -> None:
    """Prevent broken relative links across the authored Markdown manual."""
    failures: list[str] = []

    for document in documentation_files():
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith("#") or target.startswith(EXTERNAL_PREFIXES):
                continue
            path_text = unquote(target.split("#", maxsplit=1)[0])
            if not path_text:
                continue
            resolved = (document.parent / path_text).resolve()
            if not resolved.exists():
                failures.append(f"{document.relative_to(ROOT)} -> {target}")

    assert not failures, "Broken documentation links:\n" + "\n".join(failures)


def test_relative_documentation_anchors_resolve() -> None:
    """Prevent links to renamed or removed sections in local Markdown guides."""
    failures: list[str] = []

    for document in documentation_files():
        text = document.read_text(encoding="utf-8")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip().strip("<>")
            if not target or target.startswith(EXTERNAL_PREFIXES):
                continue
            path_text, separator, fragment = target.partition("#")
            if not separator or not fragment:
                continue
            resolved = document if not path_text else (document.parent / unquote(path_text)).resolve()
            if resolved.suffix.lower() != ".md" or not resolved.is_file():
                continue
            if unquote(fragment).lower() not in markdown_heading_slugs(resolved):
                failures.append(f"{document.relative_to(ROOT)} -> {target}")

    assert not failures, "Broken documentation anchors:\n" + "\n".join(failures)


def test_command_reference_covers_every_generated_script_and_tox_environment() -> None:
    """Keep operational documentation aligned with generated task entry points."""
    reference = (DOCS / "command-reference.md").read_text(encoding="utf-8")
    scripts = sorted((ROOT / "template/scripts").glob("*.py*"))
    tox_template = (ROOT / "template/tox.ini.jinja").read_text(encoding="utf-8")
    environments = set(re.findall(r"\[testenv:([a-z-]+)\]", tox_template))

    for script in scripts:
        rendered_name = script.name.removesuffix(".jinja")
        assert rendered_name in reference

    for environment in environments:
        assert f"`{environment}`" in reference


def test_generated_command_reference_is_linked_and_feature_conditional() -> None:
    """Keep the generated Sphinx reference distinct from the all-options manual."""
    generated_reference = (ROOT / "template/docs/source/command-reference.md.jinja").read_text(encoding="utf-8")
    generated_index = (ROOT / "template/docs/source/index.md.jinja").read_text(encoding="utf-8")
    generated_docs_guide = (ROOT / "template/docs/README.md.jinja").read_text(encoding="utf-8")

    assert "command-reference" in generated_index
    assert "contains only commands supported" in generated_reference
    assert "`docs/source/command-reference.md` | Template-rendered" in generated_docs_guide
    for feature in ("use_precommit", "use_notebooks", "use_dvc", "use_uml", "use_example_gallery"):
        assert feature in generated_reference

    complete_reference = (DOCS / "command-reference.md").read_text(encoding="utf-8")
    assert "This is the **complete** reference" in complete_reference
    assert "full data-science showcase" in complete_reference


def test_template_sphinx_site_indexes_the_complete_manual() -> None:
    """Keep the published template site aligned with the Markdown manual."""
    configuration = (DOCS / "conf.py").read_text(encoding="utf-8")
    index = (DOCS / "index.md").read_text(encoding="utf-8")
    with (ROOT / "pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)

    assert '"myst_parser"' in configuration
    assert 'html_theme = "furo"' in configuration
    assert "nitpicky = True" in configuration
    assert "```{toctree}" in index

    for guide in REQUIRED_GUIDES:
        if guide != "index.md":
            assert Path(guide).stem in index

    documentation_dependencies = pyproject["dependency-groups"]["docs"]
    for requirement in ("furo", "myst-parser", "sphinx", "sphinx-copybutton"):
        assert any(dependency.startswith(requirement) for dependency in documentation_dependencies)


def test_template_ci_builds_docs_and_pages_publishes_the_same_output() -> None:
    """Require one provider-neutral build contract and one Pages adapter."""
    ci_workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pages_workflow = (ROOT / ".github/workflows/docs-pages.yml").read_text(encoding="utf-8")
    build_command_parts = (
        "uv run --locked --group docs sphinx-build",
        "-W --keep-going",
        "-b html",
        "reports/sphinx/html",
    )

    for command_part in build_command_parts:
        assert command_part in ci_workflow
        assert command_part in pages_workflow

    for action in (
        "actions/configure-pages@v5",
        "actions/upload-pages-artifact@v5",
        "actions/deploy-pages@v5",
    ):
        assert action in pages_workflow

    assert "pages: write" in pages_workflow
    assert "pages: read" in pages_workflow
    assert "id-token: write" in pages_workflow
    assert "enablement: true" not in pages_workflow
    assert "name: github-pages" in pages_workflow
    assert "path: reports/sphinx/html" in pages_workflow
    assert "scripts/generate_full_example.py" not in ci_workflow
    assert "scripts/setup_project.py" not in ci_workflow
