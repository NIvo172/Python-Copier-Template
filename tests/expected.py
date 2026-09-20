"""Spec engine: structural expectations for the rendered template output.

A spec is a per-case YAML file (`tests/specs/<case>.yaml`) that captures the
*enumerated feature-sets* of a rendered project:

- ``dependency_groups``: per ``[dependency-groups]`` key, the dependency prefixes
- ``tox_environments``: every ``[testenv:...]`` declared in ``tox.ini``
- ``precommit_hooks``: hook ids grouped by ``default``/``manual`` stage
- ``ruff_select``: the top-level ``tool.ruff.lint.select`` rules
- ``per_file_ignores_keys``: the ``tool.ruff.lint.per-file-ignores`` keys

Design note: the spec deliberately does **not** track the complete file list.
That full-tree snapshot is the "static output" brittleness this refactor removes;
named-file presence stays in the focused tests (``test_source_and_layout_files``),
and prose/behaviour contracts stay in their own tests.

Regenerate every spec from the current rendered output with:

    EXPECTED_UPDATE=1 uv run --locked pytest

CI runs the tests without that env var, so drift between the committed spec and
a freshly rendered project is a hard failure with a readable set diff.
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path

import yaml

SPECS_ROOT = Path(__file__).resolve().parent / "specs"
_TOX_ENV_RE = re.compile(r"^\[testenv:([^]]+)\]$", re.MULTILINE)


def spec_path(case_id: str) -> Path:
    return SPECS_ROOT / f"{case_id}.yaml"


def load_spec(case_id: str) -> dict[str, object]:
    path = spec_path(case_id)
    if not path.is_file():
        raise FileNotFoundError(
            f"Missing spec for case {case_id!r} at {path}. Run `EXPECTED_UPDATE=1 pytest` to regenerate."
        )
    return yaml.safe_load(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def dump_spec(case_id: str, spec: dict[str, object]) -> Path:
    SPECS_ROOT.mkdir(parents=True, exist_ok=True)
    path = spec_path(case_id)
    path.write_text(yaml.safe_dump(spec, sort_keys=True, default_flow_style=False, width=120), encoding="utf-8")
    return path


def _prefixes(dependencies: object) -> list[str]:
    prefixes: list[str] = []
    for dependency in dependencies:
        if not isinstance(dependency, str):
            continue
        for marker in ("==", "~=", ">=", "<=", ">", "<", "!="):
            if marker in dependency:
                dependency = dependency.split(marker, maxsplit=1)[0]
                break
        dependency = dependency.strip()
        if dependency and dependency not in prefixes:
            prefixes.append(dependency)
    return sorted(prefixes)


def extract_structural(destination: Path) -> dict[str, object]:
    """Pull the enumerated structural surface of a rendered project out into a spec."""
    pyproject = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependency_groups: dict[str, list[str]] = {
        name: _prefixes(group) for name, group in pyproject.get("dependency-groups", {}).items()
    }

    tox_environments: list[str] = []
    if (destination / "tox.ini").is_file():
        tox_environments = sorted(set(_TOX_ENV_RE.findall((destination / "tox.ini").read_text(encoding="utf-8"))))

    precommit_hooks: dict[str, list[str]] = {}
    if (destination / ".pre-commit-config.yaml").is_file():
        config = yaml.safe_load((destination / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
        default_stage: set[str] = set()
        manual_stage: set[str] = set()
        for repo in config.get("repos", []):
            for hook in repo.get("hooks", []):
                hook_id = hook.get("id")
                if not hook_id:
                    continue
                stages = hook.get("stages")
                if stages is None or "pre-commit" in stages:
                    default_stage.add(hook_id)
                if stages and "manual" in stages:
                    manual_stage.add(hook_id)
        precommit_hooks = {"default": sorted(default_stage), "manual": sorted(manual_stage)}

    lint = pyproject.get("tool", {}).get("ruff", {}).get("lint", {})
    spec: dict[str, object] = {
        "dependency_groups": dependency_groups,
        "tox_environments": tox_environments,
        "precommit_hooks": precommit_hooks,
        "ruff_select": list(lint.get("select", [])),
        "per_file_ignores_keys": sorted(lint.get("per-file-ignores", {}).keys()),
    }
    return spec


def format_diff(spec: dict[str, object], actual: dict[str, object]) -> str:
    lines: list[str] = []
    for key in ("dependency_groups", "tox_environments", "precommit_hooks", "ruff_select", "per_file_ignores_keys"):
        expected = spec.get(key, [])
        got = actual.get(key, [])
        if expected == got:
            continue
        expected_norm = _as_set(expected)
        got_norm = _as_set(got)
        missing = sorted(expected_norm - got_norm)
        unexpected = sorted(got_norm - expected_norm)
        lines.append(f"  {key}:")
        if missing:
            lines.append(f"    in spec, missing from render: {missing}")
        if unexpected:
            lines.append(f"    rendered, not in spec: {unexpected}")
    return "\n".join(lines)


def _as_set(value: object) -> set[str]:
    if isinstance(value, dict):
        flattened: set[str] = set()
        for name, members in value.items():
            for member in _as_set(members):
                flattened.add(f"{name}:{member}")
        return flattened
    if isinstance(value, (list, tuple, set)):
        result: set[str] = set()
        for item in value:
            result.update(_as_set(item))
        return result
    return {str(value)}


def verify(destination: Path, case_id: str) -> None:
    """Compare the rendered structural surface to the committed spec.

    With ``EXPECTED_UPDATE=1`` the spec is (re)written from the render instead.
    """
    if os.environ.get("EXPECTED_UPDATE") == "1":
        dump_spec(case_id, extract_structural(destination))
        return

    spec = load_spec(case_id)
    actual = extract_structural(destination)
    diff = format_diff(spec, actual)
    if diff:
        raise AssertionError(
            f"Spec {case_id!r} does not match the rendered output.\n"
            f"Review the template change, then run `EXPECTED_UPDATE=1 pytest` and commit the diff:\n\n{diff}"
        )
