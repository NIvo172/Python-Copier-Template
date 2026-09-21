# AGENTS.md — Developing the python-project-copier-template

**Audience:** AI coding agents first; humans welcome — for whoever edits this template repository (template developers and maintainers).
**Not a user guide for generated projects.** For that, see the generated project's `AGENTS.md`, which ships as `template/AGENTS.md.jinja`.

## 0. What this repository is

A [Copier](https://copier.readthedocs.io/) template. The **product** is the `template/` directory (rendered into a new project by `copier copy` / `copier update`). Everything else — `docs/`, `tests/`, the root `pyproject.toml`, `uv.lock`, `.pre-commit-config.yaml`, `.github/workflows/`, `renovate.json` — exists to **develop and validate the template**.

Key invariants (enforced by the test suite):

1. Local validation and CI run the **same named Tox environments**.
2. Every tool's configuration has **one authoritative location** per generated project.
3. Optional capabilities are **toggle-able and updatable via `copier update`** (not replaced).
4. The generated structural surface (dependency groups, Tox envs, pre-commit hook ids/stages, Ruff `select`/`per-file-ignores`) is **pinned by committed YAML specs** in `tests/specs/*.yaml`.

## 1. Repository map

```
.
├── copier.yml                     # Questions, defaults, validators, _exclude, post-copy message
├── pyproject.toml                 # Template-dev deps (package = false, uv-managed)
├── uv.lock                        # Lockfile for developing the template itself
├── .pre-commit-config.yaml        # Hooks for the template repo itself
├── renovate.json                  # Provider-neutral dependency-update policy
├── docs/                          # Authored manual + strict Sphinx site (also a test target)
├── .github/workflows/{ci,docs-pages,renovate}.yml
├── tests/
│   ├── conftest.py                # Session-scoped render cache, parametrised fixtures
│   ├── _render.py                 # copier.run_copy helpers + CASES matrix
│   ├── expected.py                # Spec engine (structural surface → YAML)
│   ├── test_generated_projects.py # ~990 lines of generated-project contracts
│   ├── test_documentation.py      # Docs navigation / links / anchors / coverage contracts
│   └── specs/*.yaml               # Committed expected specs (regenerate with EXPECTED_UPDATE=1)
└── template/                      # ─ THE PRODUCT (rendered into a new project) ─
    ├── {{ _copier_conf.answers_file }}.jinja   → .copier-answers.yml
    ├── pyproject.toml.jinja, tox.ini.jinja, .pre-commit-config.yaml.jinja
    ├── .python-version.jinja, .editorconfig, .gitignore, .vscode/*, renovate.json
    ├── LICENSE.jinja, README.md.jinja, CONTRIBUTING.md.jinja, MAINTAINING.md.jinja
    ├── AGENTS.md.jinja                # generated project's agent task → command catalog
    ├── CODE_OF_CONDUCT.md.jinja   (only if has_other_contributors)
    ├── src/{{ package_name }}/(__init__.py.jinja, main.py.jinja, py.typed)
    ├── tests/test_main.py.jinja
    ├── scripts/init_project.py, check_package.py, check_notebooks.py,
    │           build_docs.py.jinja, generate_uml.py.jinja, clean.py
    ├── docs/                      (use_docs only)
    ├── notebooks/example.ipynb.jinja        (use_notebooks only)
    ├── examples/                 (use_example_gallery only)
    ├── configs/, data/{raw,processed,interim,external}, models/, references/, reports/figures/
    │                            (project_kind == 'data_science' only)
    ├── .dvc/, .dvcignore, dvc.yaml          (data_science + use_dvc)
    ├── .github/, .gitlab/, .bitbucket/      # CI + collaboration per provider
    ├── .github/workflows/{ci,docs-pages,renovate}.yml.jinja
    ├── .gitlab-ci.yml.jinja
    └── bitbucket-pipelines.yml.jinja
```

## 2. Everyday development workflow

```
uv sync --group dev                          # copier, jinja2, pytest, pytest-cov, pyyaml, ruff
uv run --locked pytest                       # fast suite (not slow)
uv run --locked pytest -m slow               # slow suite (build + full lifecycle)
RUN_NORMAL_PROJECT=1 uv run --locked pytest -m slow -k complete_lifecycle   # render + full tox
uv run --locked ruff check . && uv run --locked ruff format --check .
EXPECTED_UPDATE=1 uv run --locked pytest     # regenerate tests/specs/*.yaml after a structural change
```

The authoritative CI (`.github/workflows/ci.yml`) runs `pytest --cov-fail-under=80` **with `RUN_NORMAL_PROJECT=1`**, so any regression that only surfaces when a generated project is actually initialised (render → uv sync → pre-commit → tox, including the `lint` env) is caught by CI. **Never rely on `-m "not slow"` green** — it is not a green guarantee.

## 3. Adding a new Copier question / capability

1. **`copier.yml`** — add the question (`type`, `help`, `default`; optionally `choices`, `validator`, `multiselect`, `when`, `qmark: ">"`). Cross-field defaults use Jinja and are validated in tests.
2. **Gate files** — if there are files that should only render when the feature is on, add their path to the `_exclude` list with a `{% if not <flag> %}...{% endif %}` conditional so unselected features leave **no dormant directories**.
3. **`template/`** — emit the new files (static or `.jinja`) under `{{ ... }}` path tokens where needed.
4. **`pyproject.toml.jinja`** — add new dependency groups if the feature needs them, and include them in `dev` via `include-group`.
5. **`tox.ini.jinja`** — add a `[testenv:<name>]` (put it in `env_list` if it belongs to the default run, otherwise keep it on-demand like `uml`/`build`/`clean`).
6. **`.pre-commit-config.yaml.jinja`** — add the hook with `stages: [pre-commit, manual]` if it is hygiene-only (so `repo-checks` can run the manual stage without duplicating lint checks).
7. **CI** — if the feature adds a new Tox env, add it to `_expected_ci_tox_environments` and to the `ci.yml.jinja` / `.gitlab-ci.yml.jinja` / `bitbucket-pipelines.yml.jinja` env lists (all three must stay in sync).
8. **Docs** — document the question in `docs/template-options.md` (enforced by `test_documentation.py`) and include it in the generated `docs/source/command-reference.md.jinja`.
9. **Specs** — if the change shifts the dependency-group / Tox / pre-commit / Ruff surface, run:
   ```
   EXPECTED_UPDATE=1 uv run --locked pytest
   ```
   which regenerates `tests/specs/*.yaml`. Then re-run the fast suite — drift = failure.
10. **Validate**:
    ```
    uv run --locked pytest                                # structural + behavioural contracts
    RUN_NORMAL_PROJECT=1 uv run --locked pytest -m slow   # full lifecycle of a normal project
    ```

## 4. The structural spec engine

`tests/expected.py` reads a generated project's surface and compares it to the committed `tests/specs/*.yaml`:

- `dependency_groups` — every group + its top-level dependency prefixes (no version pins).
- `tox_environments` — env names that appear in `env_list` and on-demand (labels and commands too).
- `pre_commit` — hook ids by stage (`pre-commit` vs `manual`).
- `ruff` — `select` + `per-file-ignores`.

CI compares actual → spec. **Drift fails the build**, so a code/doc/spec change is only complete when all three are in lock-step. To deliberately change the expected surface: mutate the template code, then `EXPECTED_UPDATE=1 uv run --locked pytest` and **review the diff** to make sure the change is the intended one.

## 5. The six-case render matrix

`tests/_render.py` renders six variants through `copier.run_copy` and asserts on each:

1. `pyproject-hatchling` — baseline library (Hatchling, docs, pre-commit, GitHub CI).
2. `setuptools-numpy` — Setuptools backend, NumPy docstrings.
3. `data-science-full` — every optional capability on (notebooks, DVC, UML, gallery, contributors, CoC).
4. `none-no-ci` — no docs, no pre-commit, no VS Code, no CI, Setuptools.
5. `gitlab-coe` — GitLab provider with contributor + CoC.
6. `bitbucket-coe` — Bitbucket provider with contributor + CoC.

Use this matrix as the test harness for new features: a feature that should be provider-independent must hold across all six.

## 6. Copier `update` + migrations

- Generated projects commit their original answers in `.copier-answers.yml` (via `template/{{ _copier_conf.answers_file }}.jinja`).
- A project can later change any copier question with:
  ```
  copier update --vcs-ref=:current: --data <flag>=<value> ...
  ```
  The user's own files (files not in `template/`) are preserved; copier only re-renders its own files.
- **Migrations** (`_migrations` in `copier.yml`) run versioned, `unsafe=True` transforms. The suite includes `test_copier_update_runs_versioned_migration_and_preserves_project_files`.
- The template repo **must be a valid git repository** with refs when `update` is run against it — `copier update` needs a `_commit` to clone from.

## 7. Validation checklist (run before committing)

```
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked pytest -m "not slow"
EXPECTED_UPDATE=1 uv run --locked pytest          # only if you touched the surface
uv run --locked pytest                            # re-run after any EXPECTED_UPDATE
uv run --locked pytest -m slow
RUN_NORMAL_PROJECT=1 uv run --locked pytest -m slow -k complete_lifecycle
uv run --locked --group docs sphinx-build -W --keep-going -b html docs reports/sphinx/html
```

The last command is the same one the template repo's `docs-pages.yml` workflow runs; the `-W` flag turns any Sphinx warning into a failure.

## 8. Doc maintenance (this repo's `docs/`)

- The `docs/` directory is **both** the authored manual (for humans reading on GitHub) **and** a strict Sphinx site (for GitHub Pages).
- `docs/README.md` gives reading paths and the maintenance checklist.
- `docs/conf.py` enforces nitpicky + furo + myst + mermaid.
- When a new `docs/*.md` file is added, register it in `docs/README.md` (index) and `docs/index.md` (toctree) — a missing entry fails `test_documentation.py`.
- All relative links and heading anchors inside the manual are resolved by `test_documentation.py`; broken links fail.

## 9. Known gotchas

- **Do not add `# type: ignore`** to silence `mypy`; add type stubs or narrow the scope instead.
- **Do not pin exact versions** in the generated `pyproject.toml.jinja` for new dependencies — use the `>=X.Y` convention already in the file.
- **Do not put user-authored content in `template/`** — everything there is re-rendered and user changes are lost on `copier update`.
- **Do not add new `_exclude` patterns** without adding a corresponding test in `test_generated_projects.py` (e.g. "when `use_dvc` is off, `.dvc` and `dvc.yaml` are absent").
- **`pyproject.toml` (root) is `package = false`** — it is a tooling project for the template repo, not the product. Its `pyproject.toml` is only linted by the template's own pre-commit, NOT by the generated project's `lint` env.

## 10. Release & publishing (template repo)

- The template has no PyPI release; it is consumed from Git. Tag a version when the questions / structure stabilise: `git tag v0.1.0`.
- The root `pyproject.toml` is versioned but not published; treat it as a pin for the template-dev environment.
- Renovate (`renovate.json`) maintains the template-dev deps across every manager; CI does not publish anything.

## 11. Quick commands (template dev)

```
uv sync --group dev
uv run --locked pytest
uv run --locked pytest -m slow
RUN_NORMAL_PROJECT=1 uv run --locked pytest -m slow -k complete_lifecycle
EXPECTED_UPDATE=1 uv run --locked pytest
uv run --locked ruff check . && uv run --locked ruff format --check .
uv run --locked --group docs sphinx-build -W --keep-going -b html docs reports/sphinx/html
```

## 12. Testing the "other" provider paths

`test_generated_projects.py::test_ci_provider_contract` asserts that for each of `github` / `gitlab` / `bitbucket` / `none` the generated repo has (or lacks) the correct CI files and that the Tox env list referenced in each CI workflow matches `_expected_ci_tox_environments`. If you add a new env, the test suite catches when any one provider drifts.
