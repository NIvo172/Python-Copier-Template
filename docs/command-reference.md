# Command reference

This guide is the operational command index for the template repository and generated projects. Run commands from the repository root unless noted otherwise.

## Documentation scopes

This is the **complete** reference: it covers the template repository and every command that any supported generated configuration can expose. A generated project with Sphinx enabled receives `docs/source/command-reference.md`, rendered from the selected Copier answers so that it omits unavailable tools. The companion full data-science showcase adds concrete walkthroughs, expected artefacts, and an exhaustive validation example on top of that generated reference.

The template reference defines the command contract. Generated Sphinx documentation narrows it to one project, while showcase documentation demonstrates it; the latter two should not invent alternative commands for the same task.

## Command conventions

- `uv run --locked ...` runs against the committed dependency state and is preferred for validation.
- `uv run ...` may refresh the lock or environment and is appropriate during intentional dependency work.
- Tox is the supported project-level task interface shared by contributors and CI.
- Commands after `tox run -e <environment> --` are forwarded to the environment's underlying command.
- Optional Tox environments exist only when the corresponding Copier feature is enabled.

## Template repository

| Goal | Command | Effect |
| --- | --- | --- |
| Synchronise template and documentation tools | `uv sync --locked --group docs` | Creates/updates `.venv` from the committed template lock without changing it |
| Run structural contracts | `uv run pytest` | Renders representative Copier configurations and tests migrations/documentation contracts |
| Lint template Python | `uv run ruff check .` | Reports import, correctness, modernization, and style problems |
| Check formatting | `uv run ruff format --check .` | Reports Python files that require formatting |
| Apply formatting | `uv run ruff format .` | Rewrites Python formatting |
| Test generated distributions | `RUN_GENERATED_BUILDS=1 uv run pytest` | Enables slower build checks for rendered cases |
| Test a normal project lifecycle | `RUN_NORMAL_PROJECT=1 uv run pytest tests/test_generated_projects.py -k normal_project_complete_lifecycle` | Renders the normal data-science regression configuration, initialises it, then runs Tox and cleanliness checks |
| Build the template manual | `uv run --locked --group docs sphinx-build -W --keep-going -b html docs reports/sphinx/html` | Builds the complete template Sphinx site and fails on warnings |

## Generate a project

| Source | Command |
| --- | --- |
| Current local checkout | `uvx copier copy --vcs-ref HEAD . ../my-project` |
| Tagged local checkout | `uvx copier copy --vcs-ref v1.0.0 . ../my-project` |
| Tagged remote repository | `uvx copier copy --vcs-ref v1.0.0 <template-url> my-project` |

Use released template tags for reproducible generation. Copier stores the source and selected revision in `.copier-answers.yml` for later updates.

## One-time generated-project initialisation

```bash
uv run scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
```

| Option | Default | Meaning |
| --- | --- | --- |
| `--git-name NAME` | `John Doe` | Repository-local Git author name |
| `--git-email EMAIL` | `john.doe@example.com` | Repository-local Git author email |
| `--tag TAG` | `v0.0.1` | Initial version tag |

The script is resumable after many partial failures and never moves an existing tag that points to another commit. It streams output to the terminal and creates no log. Run `uv run --locked tox` separately after initialisation.

## Dependency operations

| Goal | Command |
| --- | --- |
| Synchronise an established checkout | `uv sync --locked` |
| Add a runtime dependency | `uv add <package>` |
| Remove a runtime dependency | `uv remove <package>` |
| Add a test dependency | `uv add --group test <package>` |
| Add a lint/type dependency | `uv add --group lint <package>` |
| Add a documentation dependency | `uv add --group docs <package>` |
| Add a notebook dependency | `uv add --group notebooks <package>` |
| Add a DVC dependency | `uv add --group dvc <package>` |
| Resolve the lock | `uv lock` |
| Verify the lock without changing it | `uv lock --check` |
| Export a pip-compatible view | `uv export --frozen --format requirements.txt --output-file requirements.txt` |

Commit `pyproject.toml` and `uv.lock` together after intentional dependency changes. Do not use an exported `requirements.txt` as a second declaration source.

## Tox environments

| Environment | Command | Condition | Contract |
| --- | --- | --- | --- |
| Default | `uv run --locked tox` | Always | Runs the configured minimum-version and validation environment list |
| `pre-commit` | `uv run --locked tox run -e pre-commit` | Pre-commit | Runs every hook against all files |
| `repo-checks` | `uv run --locked tox run -e repo-checks` | Pre-commit | Runs the manual-stage repository-hygiene subset used by CI |
| `lock` | `uv run --locked tox run -e lock` | Always | Requires `uv.lock` to match `pyproject.toml` |
| `lint` | `uv run --locked tox run -e lint` | Always | Checks docstrings, Ruff, formatting, and strict Mypy |
| `pyXY` | `uv run --locked tox run -e py311` | Selected Python | Builds a wheel, installs it, and runs pytest |
| Test matrix | `uv run --locked tox run -m test` | Always | Runs every selected `pyXY` environment |
| `notebooks` | `uv run --locked tox run -e notebooks` | Notebooks | Checks Python-cell docstrings and exploratory-output hygiene |
| `dvc` | `uv run --locked tox run -e dvc` | Data science + DVC | Requires DVC metadata and pipeline outputs to be current |
| `uml` | `uv run --locked tox run -e uml` | Docs + UML | Generates Pyreverse/Mermaid sources |
| `docs` | `uv run --locked tox run -e docs` | Documentation | Builds API coverage and strict HTML |
| `package-check` | `uv run --locked tox run -e package-check` | Always | Builds fresh sdist/wheel and validates metadata/contents |
| `build` | `uv run --locked tox run -e build` | Always | Builds sdist and wheel without the extra release checks |
| `clean` | `uv run --locked tox run -e clean` | Always | Removes generated reports, builds, and generated documentation sources |

List the exact environments rendered for a project:

```bash
uv run tox list
```

## Generated script entry points

| Script | Availability | Purpose |
| --- | --- | --- |
| `scripts/init_project.py` | Always | One-time Git, lock, generated-state, and initial-tag workflow |
| `scripts/clean.py` | Always | Cross-platform removal of generated reports, builds, and generated documentation sources |
| `scripts/check_package.py` | Always | Fresh sdist/wheel build, strict metadata check, and wheel-content validation |
| `scripts/build_docs.py` | Documentation | Strict HTML/API-coverage builds and documentation cleanup |
| `scripts/generate_uml.py` | Documentation + UML | Pyreverse execution and Mermaid source generation |
| `scripts/check_notebooks.py` | Notebooks | Recursive exploratory-notebook output/metadata verification |

Normal contributor and CI operations invoke recurring scripts through Tox. `init_project.py` is the exception: it is intentionally run directly once before the repository becomes an established checkout.

## Focused tests

```bash
uv run --locked tox run -e py311 -- -k <expression>
uv run --locked tox run -e py311 -- tests/test_module.py::test_name
uv run --locked tox run -e py311 -- --log-cli-level=INFO
```

Replace `py311` with an interpreter selected by the project. Direct `uv run --locked --group test pytest` is faster for iteration but tests the development environment rather than the built wheel.

## Documentation commands

### Template repository documentation

| Goal | Command | Output |
| --- | --- | --- |
| Strict template site build | `uv run --locked --group docs sphinx-build -W --keep-going -b html docs reports/sphinx/html` | `reports/sphinx/html/` |
| Preview the built site | `uv run --locked python -m http.server --directory reports/sphinx/html 8000` | Local site at port 8000 |

The Sphinx sources are the Markdown files in `docs/`; GitHub Pages publishes the same static output through `.github/workflows/docs-pages.yml`. See [Publishing](publishing.md) for one-time repository configuration and provider-neutral alternatives.

### Generated-project documentation

| Goal | Command | Output |
| --- | --- | --- |
| Complete strict build | `uv run --locked tox run -e docs` | HTML plus API coverage |
| HTML only | `uv run --locked tox run -e docs -- html` | `reports/sphinx/html/` |
| API coverage only | `uv run --locked tox run -e docs -- coverage` | `reports/sphinx/coverage/` |
| Remove docs output | `uv run --locked tox run -e docs -- clean` | Deletes generated Sphinx sources and output |
| Generate UML only | `uv run --locked tox run -e uml` | Mermaid sources under `docs/source/diagrams/` |

Sphinx warnings fail the build. API coverage also fails when public symbols are undocumented or modules cannot be imported.

## Notebook commands

```bash
uv run --group notebooks jupyter lab
uv run --locked tox run -e notebooks
```

Exploratory notebooks under `notebooks/` should not retain removable output or volatile execution metadata. Documentation notebooks have a separate authored-output policy described in the generated `docs/README.md`.

## DVC commands

| Goal | Command |
| --- | --- |
| Inspect pipeline state | `uv run dvc status` |
| Reproduce changed stages | `uv run dvc repro` |
| Show scalar results | `uv run dvc metrics show` |
| Render/inspect plot declarations | `uv run dvc plots show` |
| Run a declared experiment | `uv run dvc exp run` |
| Add a shared remote | `uv run dvc remote add -d storage <remote-url>` |
| Upload tracked data/model objects | `uv run dvc push` |
| Retrieve tracked objects | `uv run dvc pull` |

The template configures no DVC storage remote or credentials.

## Copier update commands

```bash
copier update --pretend --vcs-ref=v1.1.0
copier update --vcs-ref=v1.1.0
uv lock
uv sync
uv run --locked tox
```

Use `--vcs-ref=:current:` only when intentionally following the source recorded in `.copier-answers.yml`. Use a concrete tag for reproducible upgrades.

## Git and version diagnostics

```bash
git status --short
git log --oneline --decorate -5
git describe --tags --always --dirty
git tag --points-at HEAD
git show-ref --tags
```

Both supported build backends derive versions from Git tags. A shallow checkout or missing tags can therefore change the computed package version.
