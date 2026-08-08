# Template architecture

This guide explains the generated dependency, task, validation, documentation, and CI model. Start with the [documentation home](README.md) for audience-specific reading paths.

## Responsibility boundaries

| Component | Responsibility | Main configuration |
| --- | --- | --- |
| Copier | Render and update projects | `copier.yml`, `.copier-answers.yml` |
| `uv` | Resolve, lock, synchronise, run tools, export dependency views, and build distributions | `pyproject.toml`, `uv.lock` |
| Tox | Define isolated tasks shared by developers and CI | `tox.ini` |
| pre-commit | Run fast repository checks and automatic fixes | `.pre-commit-config.yaml` |
| Ruff | Lint and format Python and notebook code | `pyproject.toml` |
| Mypy | Run strict static type analysis | `pyproject.toml` |
| pytest | Execute tests and write test and coverage reports | `pyproject.toml` |
| Sphinx | Build documentation and verify public API documentation coverage | `docs/source/conf.py` |
| DVC | Track data artefacts and validate pipeline state | `dvc.yaml`, `dvc.lock`, `.dvc/` |
| Repository provider | Route ownership and prefill contribution descriptions when collaboration files are enabled | Provider-native `CODEOWNERS` and request templates |
| Renovate | Propose updates across every detected dependency manager after a repository owner enables the bot | `renovate.json` |

`pyproject.toml` is the generated project's metadata and Python-tool source of truth. Sphinx reads project metadata from it and gets the installed version through `importlib.metadata`.

## Dependency model

`pyproject.toml` declares runtime dependencies and reusable development groups. `uv.lock` is the authoritative resolved state after initialisation.

| Group | Purpose | Presence |
| --- | --- | --- |
| `test` | pytest, coverage, and report plugins | Always |
| `lint` | docstring formatting, Ruff, Mypy, and optional repository/notebook tools | Always |
| `package-check` | Twine and wheel-content validation | Always |
| `dvc` | DVC CLI | Data science with DVC |
| `notebooks` | JupyterLab and IPykernel | Notebooks enabled |
| `docs` | Sphinx and selected extensions | Documentation enabled |
| `dev` | Every applicable group plus Tox, tox-uv, and pytest-sugar | Always |

Tox selects these groups through `dependency_groups`. Requirements should not normally be repeated under Tox `deps`; that field is reserved for genuinely environment-specific bootstrap dependencies.

Contributors synchronise a committed lock without changing it:

```bash
uv sync --locked
```

Intentional dependency changes use:

```bash
uv add <package>
uv remove <package>
uv add --group test <package>
uv lock
uv sync
```

A pip-compatible view can be exported without creating a second source of truth:

```bash
uv export --frozen --format requirements.txt --output-file requirements.txt
```

The checked-in Renovate configuration enables every dependency manager that Renovate detects. Depending on the rendered project, this includes PEP 621 metadata, `uv.lock`, pre-commit hooks, GitHub Actions, GitLab CI or Bitbucket Pipelines dependencies, container images, and any additional supported dependency files added later. Weekly lock-file maintenance also refreshes compatible transitive dependencies. Routine minor, patch, pin, and digest updates are grouped; major upgrades remain separate for focused review.

Renovate changes dependency references only; enabling it does not otherwise rewrite CI jobs or change their permissions, triggers, or validation policy. Renovate is provider-neutral and remains inactive until installed or enabled for the repository.

## Tox execution model

Tox is the public task API. CI provisions runners and invokes the same named environments used locally; it does not duplicate tool policy in provider YAML.

| Task | Preferred command | Important distinction |
| --- | --- | --- |
| Default suite | `uv run --locked tox` | Runs the configured minimum-version and validation environments |
| Every pre-commit hook | `uv run --locked tox run -e pre-commit` | Present only with pre-commit |
| CI repository hygiene | `uv run --locked tox run -e repo-checks` | Narrow manual-stage hook subset |
| Lock consistency | `uv run --locked tox run -e lock` | Checks `uv.lock` against `pyproject.toml` |
| Static validation | `uv run --locked tox run -e lint` | Docstrings, Ruff, formatting, and strict Mypy |
| Tests on Python X.Y | `uv run --locked tox run -e pyXY` | Builds and tests the installed wheel |
| Complete Python matrix | `uv run --locked tox run -m test` | Discovers all environments labelled `test` |
| Notebook validation | `uv run --locked tox run -e notebooks` | Present only with notebooks |
| DVC state | `uv run --locked tox run -e dvc` | Present only with data science and DVC |
| UML | `uv run --locked tox run -e uml` | Present only with documentation and UML |
| Complete docs | `uv run --locked tox run -e docs` | API coverage plus HTML |
| HTML docs | `uv run --locked tox run -e docs -- html` | HTML only |
| API docs coverage | `uv run --locked tox run -e docs -- coverage` | Fails for undocumented public API or imports |
| Clean docs | `uv run --locked tox run -e docs -- clean` | Removes Sphinx output and generated sources |
| Distribution validation | `uv run --locked tox run -e package-check` | Builds and validates sdist and wheel |
| Build | `uv run --locked tox run -e build` | Builds without the additional release checks |
| Clean | `uv run --locked tox run -e clean` | Removes generated output |

The `pyXY` environments package and install a wheel before testing. A direct `uv run --locked --group test pytest` command tests the synchronised development environment instead.

Data-science projects should keep DVC declarations semantically complete: stage commands consume every listed parameter, scalar results use `metrics`, comparison series use `plots`, and deterministic metadata records content-based input provenance.

Pytest uses branch coverage with an 80% threshold. Live console logging is disabled by default but can be enabled for one run:

```bash
uv run --locked --group test pytest --log-cli-level=INFO
uv run --locked tox run -e py311 -- --log-cli-level=INFO
```

## Task-script boundary

Short, declarative, cross-platform commands live directly in `tox.ini`. Python scripts are retained for stateful workflows, filesystem discovery, artefact iteration, policy checks, failure aggregation, or portable cleanup.

| Script | Generated when | Lifecycle | Responsibility |
| --- | --- | --- | --- |
| `scripts/init_project.py` | Always | One-time bootstrap | Git, lock, generated state, and initial tag |
| `scripts/clean.py` | Always | Recurring maintenance | Cross-platform generated-output cleanup |
| `scripts/check_package.py` | Always | Recurring validation | Fresh builds, artefact discovery, Twine, and wheel-content checks |
| `scripts/build_docs.py` | Documentation | Recurring validation | Strict Sphinx builders, API coverage, optional UML, aggregation, and cleanup |
| `scripts/generate_uml.py` | Documentation and UML | Recurring generation | Pyreverse invocation and Mermaid output |
| `scripts/check_notebooks.py` | Notebooks | Recurring validation | Recursive notebook output/metadata policy |

`init_project.py` is never a normal Tox or CI task. It remains as a Copier-managed record of the initial repository bootstrap; validation is run separately through Tox.

## Package validation

`scripts/check_package.py`:

1. removes stale `dist/` output;
2. runs `uv build`;
3. requires both a source distribution and wheel;
4. runs `twine check --strict` on all distributions; and
5. runs `check-wheel-contents` on every wheel.

Both supported backends derive versions from Git:

| Choice | Build backend | Version provider |
| --- | --- | --- |
| `hatchling` | Hatchling | `hatch-vcs` |
| `setuptools` | Setuptools | `setuptools-scm` |

## Documentation model

The template repository builds this complete manual directly from the Markdown files in `docs/`. `docs/conf.py` defines a strict MyST/Sphinx/Furo build, `docs/index.md` owns published navigation, and `reports/sphinx/html/` is the provider-neutral static output. Template CI validates that build; `.github/workflows/docs-pages.yml` is only the GitHub Pages publication adapter.

Documentation-enabled projects generate:

- a concise root README included as the **Project README** page;
- `docs/README.md`, the detailed documentation-author guide;
- MyST Markdown and reStructuredText support;
- recursive Autosummary API pages with project-owned templates;
- strict HTML and API-coverage builders;
- optional MyST-NB, Sphinx-Gallery, and Mermaid support; and
- stable output under `reports/sphinx/`.

Sphinx warnings fail the build. API coverage fails when public functions/classes are undocumented or configured modules cannot be imported. Notebook execution is disabled during documentation builds.

Generated source artefacts are ignored:

- `docs/source/_autosummary/`;
- `docs/source/auto_examples/` and `sg_execution_times.rst`; and
- generated `docs/source/diagrams/*.mmd`.

## CI model

Provider workflows invoke named Tox environments for repository hygiene, lock checks, lint, the selected Python matrix, optional features, documentation, and package validation.

| Provider | File | Behavior |
| --- | --- | --- |
| GitHub Actions | `.github/workflows/ci.yml` | Cancels superseded runs and uploads reports/docs/distributions |
| GitLab CI | `.gitlab-ci.yml` | Uses interruptible jobs and retains artefacts |
| Bitbucket Pipelines | `bitbucket-pipelines.yml` | Uses the same Tox contract without repository-YAML auto-cancel |
| None | No CI file | Local Tox tasks remain unchanged |

CI fetches complete Git history so version providers can see tags.

## Collaboration model

Collaboration is a provider-neutral Copier capability with provider-native output:

| Provider | Ownership file | Review template | Bug template |
| --- | --- | --- | --- |
| GitHub | `.github/CODEOWNERS` | `.github/PULL_REQUEST_TEMPLATE.md` | Structured issue form |
| GitLab | `.gitlab/CODEOWNERS` | `.gitlab/merge_request_templates/Default.md` | Markdown issue template |
| Bitbucket | `.bitbucket/CODEOWNERS` | `.bitbucket/pull_request_template.md` | Contributor-guide checklist |

The common `CODE_OF_CONDUCT.md` and contributor instructions are independent of the provider. Generated repository files route and document review but do not modify remote protected-branch, approval, or permission settings.

## Tool reference

| Area | Documentation |
| --- | --- |
| Copier | [copier.readthedocs.io](https://copier.readthedocs.io/) |
| `uv` | [docs.astral.sh/uv](https://docs.astral.sh/uv/) |
| Tox | [tox.wiki](https://tox.wiki/) |
| pre-commit | [pre-commit.com](https://pre-commit.com/) |
| Ruff | [docs.astral.sh/ruff](https://docs.astral.sh/ruff/) |
| Mypy | [mypy.readthedocs.io](https://mypy.readthedocs.io/) |
| pytest | [docs.pytest.org](https://docs.pytest.org/) |
| Coverage.py | [coverage.readthedocs.io](https://coverage.readthedocs.io/) |
| Hatchling | [hatch.pypa.io](https://hatch.pypa.io/latest/config/build/) |
| Setuptools | [setuptools.pypa.io](https://setuptools.pypa.io/) |
| Sphinx | [sphinx-doc.org](https://www.sphinx-doc.org/en/master/) |
| MyST-NB | [myst-nb.readthedocs.io](https://myst-nb.readthedocs.io/) |
| Sphinx-Gallery | [sphinx-gallery.github.io](https://sphinx-gallery.github.io/) |
| Pyreverse | [pylint.pycqa.org](https://pylint.pycqa.org/en/stable/additional_tools/pyreverse/index.html) |
| Mermaid | [mermaid.js.org](https://mermaid.js.org/intro/) |
| JupyterLab | [jupyterlab.readthedocs.io](https://jupyterlab.readthedocs.io/en/stable/) |
| DVC | [dvc.org/doc](https://dvc.org/doc) |
| GitHub Actions | [docs.github.com/actions](https://docs.github.com/actions) |
| GitLab CI/CD | [docs.gitlab.com/ci](https://docs.gitlab.com/ci/) |
| Bitbucket Pipelines | [support.atlassian.com](https://support.atlassian.com/bitbucket-cloud/docs/get-started-with-bitbucket-pipelines/) |
