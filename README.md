# Python Project Copier Template

A Copier template for modern pure-Python libraries, command-line applications, and data-science packages. It uses `uv` for dependency and environment management, Tox as the shared local/CI task interface, and Git tags as the package-version source.

This template is designed around three key principles:

1. **Local validation and CI** invoke the same named Tox environments for consistent testing
2. **Project metadata and tool configuration** each have one authoritative location to avoid duplication
3. **Optional capabilities** remain updateable through Copier rather than requiring project replacement

## Quick start

### Generate a project

From a local template checkout:

```bash
uvx copier copy --vcs-ref HEAD . ../my-project
uv run ../my-project/scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
  --tag       "v0.0.1"
cd ../my-project
uv run --locked tox
```

From a tagged remote template:

```bash
uvx copier copy gh:YOUR_ACCOUNT/python-project-template my-project
uv run my-project/scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
  --tag       "v0.0.1"
cd my-project
uv run --locked tox
```

The initialisation script creates Git history, `uv.lock`, optional DVC state, and the default `v0.0.1` tag. Tox is intentionally kept separate from the one-time initialization process, so developers and CI can use the same reproducible validation command throughout the project lifecycle.

### Inspect the complete data-science showcase

A complete all-features project lives in the companion [`full-data-science-showcase`](https://github.com/NIvo172/full-data-science-showcase) repository. That repository owns its deterministic CSV/DVC pipeline, integration tests, narrative documentation, and exhaustive command-validation driver.

## Requirements

- Python 3.11 or newer for template development and generated initialisation scripts
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
- [Git](https://git-scm.com/downloads)

## What the template generates

Every project includes:

- a typed `src/` package layout
- PEP 621 metadata and dependency groups in `pyproject.toml`
- Hatchling/hatch-vcs or Setuptools/setuptools-scm for building
- Git-derived PEP 440 versions
- `uv.lock` after initialisation
- Ruff, strict Mypy, pytest, branch coverage, and structured reports
- Tox tasks shared by contributors and CI
- package build and distribution validation
- provider-neutral dependency updates across every source Renovate detects
- a concise project README, contributor guide, and maintainer guide
- an MIT licence
- `.copier-answers.yml` for future template updates

Optional capabilities include Sphinx, MyST-NB, Sphinx-Gallery, Pyreverse/Mermaid UML, JupyterLab, data-science directories, DVC, pre-commit, VS Code settings, provider-specific CI, and provider-native collaboration files.

## Documentation map

The template repository keeps its landing page short. Detailed reference material lives under `docs/` and is also built as a strict Sphinx site for GitHub Pages:

| Guide                                                          | Contents                                                                                                 |
| -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [`docs/index.md`](docs/index.md)                               | Published Sphinx landing page and complete site navigation                                               |
| [`docs/README.md`](docs/README.md)                             | Documentation home, reading paths, guide index, and documentation maintenance policy                     |
| [`docs/getting-started.md`](docs/getting-started.md)           | End-to-end project generation, bootstrap, remote setup, and first contributor workflow                   |
| [`docs/template-options.md`](docs/template-options.md)         | Every Copier answer, conditional feature rule, and generated layout                                      |
| [`docs/architecture.md`](docs/architecture.md)                 | Tool responsibilities, dependency model, Tox environments, scripts, reports, documentation, and CI       |
| [`docs/command-reference.md`](docs/command-reference.md)       | Template, initialisation, dependency, Tox, documentation, notebook, DVC, update, and diagnostic commands |
| [`docs/ci-and-collaboration.md`](docs/ci-and-collaboration.md) | Provider files, shared CI contract, artefacts, owners, remote settings, and Renovate                     |
| [`docs/data-science.md`](docs/data-science.md)                 | Data layout, DVC contracts, metrics, plots, provenance, experiments, notebooks, and storage              |
| [`docs/maintenance.md`](docs/maintenance.md)                   | Initialisation, template development, focused validation, Copier updates, and versioning                 |
| [`docs/updates-and-releases.md`](docs/updates-and-releases.md) | Dependencies, Copier migrations, template/project releases, tags, and rollback boundaries                |
| [`docs/publishing.md`](docs/publishing.md)                     | Provider-neutral Sphinx build, GitHub Pages deployment, and publication troubleshooting                  |
| [`docs/troubleshooting.md`](docs/troubleshooting.md)           | Initialisation, lock, Python, DVC, documentation, update, and CI failure recovery                        |

Generated projects use a parallel audience-based structure:

| Generated file    | Audience                                        |
| ----------------- | ----------------------------------------------- |
| `README.md`       | Package users and evaluators                    |
| `CONTRIBUTING.md` | Developers working in an established repository |
| `MAINTAINING.md`  | Initial project owner and long-term maintainers |
| `docs/README.md`  | Documentation authors, when Sphinx is enabled   |

## Feature summary

| Area               | Choices                                                                                                  |
| ------------------ | -------------------------------------------------------------------------------------------------------- |
| Project kind       | Library, command-line application, or data-science package                                               |
| Build backend      | Hatchling/hatch-vcs or Setuptools/setuptools-scm                                                         |
| Python             | Minimum and tested versions from 3.11 through 3.14                                                       |
| Docstrings         | Google or NumPy                                                                                          |
| Documentation      | Sphinx/Furo with optional notebooks, gallery, and UML                                                    |
| Data               | Optional data-science layout and optional DVC                                                            |
| Repository tooling | Optional pre-commit and VS Code settings                                                                 |
| Dependency updates | Renovate for all detected managers, including Python, lockfiles, hooks, CI actions, and container images |
| CI                 | GitHub Actions, GitLab CI, Bitbucket Pipelines, or none                                                  |
| Collaboration      | Optional CODEOWNERS, change/bug templates, and code of conduct                                           |

Conditional files are excluded during Copier rendering. Unselected integrations do not remain as dormant directories or configuration.

## Generated project workflow

After the one-time bootstrap, contributors clone the established repository and run:

```bash
uv sync --locked
uv run --locked tox
```

When pre-commit is enabled:

```bash
uv run pre-commit install
```

Dependency changes use `uv add`, `uv remove`, and `uv lock`. Named Tox environments provide focused checks:

```bash
uv run --locked tox run -e lint
uv run --locked tox run -m test
uv run --locked tox run -e package-check
```

Optional environments such as `docs`, `notebooks`, `dvc`, and `uml` are rendered only when applicable. See the generated `CONTRIBUTING.md` for daily development and `MAINTAINING.md` for bootstrap, versioning, CI, and Copier updates.

## Develop the template

Synchronise the template environment and run its structural checks:

```bash
uv sync --locked --group docs
uv run --locked pytest
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked --group docs sphinx-build \
  -W --keep-going \
  -b html \
  docs \
  reports/sphinx/html
```

The tests render combinations covering both build backends, all project kinds, optional feature removal, both docstring conventions, and every CI provider. Documentation contracts also validate guide navigation, local links and anchors, rendered commands, scripts, includes, Sphinx toctrees, and the publication workflow. Pull requests build the template manual with warnings treated as errors; pushes to `main` can publish the same output through GitHub Pages.

Generated-project integration checks are opt-in:

```bash
RUN_GENERATED_BUILDS=1 uv run pytest
RUN_NORMAL_PROJECT=1 uv run pytest tests/test_generated_projects.py -k normal_project_complete_lifecycle
```

The standard suite renders representative configurations and checks their files and contracts. The opt-in normal-project lifecycle runs the generated initialisation script and the separate Tox validation command. Exhaustive all-features validation belongs to the companion showcase repository, keeping this template package focused on rendering and update behavior.

## Source map

| Path                               | Purpose                                                                               |
| ---------------------------------- | ------------------------------------------------------------------------------------- |
| `copier.yml`                       | Questions, validation, exclusions, and post-copy instructions                         |
| `template/`                        | Jinja-rendered generated-project source                                               |
| `template/README.md.jinja`         | Generated user-facing landing page                                                    |
| `template/CONTRIBUTING.md.jinja`   | Generated contributor workflow                                                        |
| `template/MAINTAINING.md.jinja`    | Generated maintainer workflow                                                         |
| `template/docs/README.md.jinja`    | Optional generated documentation-author guide                                         |
| `docs/`                            | Complete template manual, Sphinx configuration, navigation, and publication guide     |
| `.github/workflows/docs-pages.yml` | GitHub Pages adapter for the provider-neutral Sphinx build                            |
| `tests/test_documentation.py`      | Template-manual navigation, links, anchors, option, command, script, and Tox coverage |
| `tests/test_generated_projects.py` | Multi-configuration structure and generated-documentation validation                  |

When changing generated behavior, edit the corresponding source under `template/`, update conditional rules in `copier.yml` when needed, and extend structural tests. Do not patch a previously generated project as the source of truth.
