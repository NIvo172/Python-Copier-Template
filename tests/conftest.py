"""Shared pytest fixtures for the template test-suite.

Design:
- `overrides` is a parameterised fixture that yields one of `CASES`. Every test
  that requests `rendered` is implicitly parameterised across all cases.
- `rendered` is a *session-scoped* render cache keyed by a hash of the case
  overrides. Each case is rendered once per pytest process (not per test), so
  the ~14 tests that split the old monolith together pay 6 renders (one per
  case) instead of 84.
- Tests that need a scratch directory of their own still use `tmp_path` (which
  stays function-scoped and is cleaned up by pytest).

Why a module-level cache and a `tempfile` dir instead of `tmp_path_factory`:
the pytest `tmp_path_factory` fixture is function-scoped, so a session cache
could not safely depend on it. The cache is cleaned up in `pytest_sessionfinish`.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest
from _render import (  # noqa: F401  (imported here for convenience)
    BASE_ANSWERS,
    CASE_IDS,
    CASES,
    CURRENT_PYTHON,
    NORMAL_PROJECT_REGRESSION_OVERRIDES,
    TEMPLATE_ROOT,
    case_cache_id,
    generated_documentation,
    has_dependency,
    load_toml,
    render_generated_project,
)

_RENDER_CACHE: dict[str, tuple[Path, dict[str, object]]] = {}
_SESSION_ROOT: Path | None = None


def _session_root() -> Path:
    global _SESSION_ROOT
    if _SESSION_ROOT is None:
        _SESSION_ROOT = Path(tempfile.mkdtemp(prefix="copier-template-test-"))
    return _SESSION_ROOT


@pytest.fixture(params=CASES, ids=CASE_IDS)
def overrides(request: pytest.FixtureRequest) -> dict[str, object]:
    """Yield the active case overrides; tests that request `rendered` are parameterised across all cases."""
    return request.param


@pytest.fixture
def rendered(overrides: dict[str, object]) -> tuple[Path, dict[str, object]]:
    """Yield `(destination, answers)` for the shared render of this case."""
    key = case_cache_id(overrides)
    cached = _RENDER_CACHE.get(key)
    if cached is None:
        destination = _session_root() / key
        answers = render_generated_project(destination, overrides)
        cached = (destination, answers)
        _RENDER_CACHE[key] = cached
    return cached


@pytest.fixture
def destination(rendered: tuple[Path, dict[str, object]]) -> Path:
    """Just the destination directory of a rendered case."""
    return rendered[0]


@pytest.fixture
def answers(rendered: tuple[Path, dict[str, object]]) -> dict[str, object]:
    """Just the answers dict for the active case."""
    return rendered[1]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    global _SESSION_ROOT
    if _SESSION_ROOT is not None:
        shutil.rmtree(_SESSION_ROOT, ignore_errors=True)
        _SESSION_ROOT = None
