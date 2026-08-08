# Template options

This guide documents every Copier answer, its validation, and the files or behavior it controls.

For a guided first render, see [Getting started](getting-started.md). For automation, store ordinary answer keys in a YAML file and pass it to Copier:

```bash
uvx copier copy --data-file copier-data.yml --defaults --vcs-ref=<template-tag> <template-url> <destination>
```

Do not copy `_src_path`, `_commit`, or other internal keys from a generated `.copier-answers.yml` into a reusable input file. Keep secrets out of answer files.

## Project identity

| Answer | Allowed values and default | Effect |
| --- | --- | --- |
| `project_name` | Text; `My Python Project` | Human-readable project and documentation title |
| `project_description` | Text; `A modern pure-Python project` | PEP 621 description and README summary |
| `distribution_name` | Lowercase letters, digits, and single hyphens; derived from `project_name` | Package-index and installed-distribution name |
| `package_name` | Lowercase Python identifier; derived from `distribution_name` | Import-package directory under `src/` |
| `user_name` | Text; `Your Name` | PEP 621 author metadata |
| `user_email` | Text; `you@example.com` | PEP 621 author metadata |

Author metadata does not set Git identity. The generated initialisation script accepts separate `--git-name` and `--git-email` options.

## Project URLs

| Answer | Effect when non-empty |
| --- | --- |
| `repository_url` | Adds `Repository` and an `Issues` URL formed by appending `/issues` |
| `homepage_url` | Adds `Homepage` |
| `documentation_url` | Adds `Documentation` |
| `changelog_url` | Adds `Changelog` |

URLs are inserted into `[project.urls]` in `pyproject.toml`. Copier does not test their reachability.

## Python and packaging

| Answer | Choices and default | Effect |
| --- | --- | --- |
| `minimum_python_version` | 3.11, 3.12, 3.13, or 3.14; default 3.11 | Sets `requires-python`, `.python-version`, Ruff/Mypy targets, and the default Python Tox environment |
| `python_versions` | One or more versions at or above the minimum | Creates `pyXY` Tox environments, package classifiers, and the CI test matrix |
| `build_backend` | `hatchling` or `setuptools`; default `hatchling` | Selects Hatchling/hatch-vcs or Setuptools/setuptools-scm |
| `project_kind` | `library`, `application`, or `data_science`; default `library` | Controls the console entry point and data-science layout |
| `docstring_style` | `google` or `numpy`; default `google` | Configures Ruff pydocstyle and `format-docstring` |

`python_versions` defaults to every offered version from the selected minimum through Python 3.14. The minimum must be included, and lower versions are rejected.

Both build backends derive versions from Git. A build from tag `v0.0.1` receives version `0.0.1`; later commits receive a PEP 440 development version derived from repository state.

## Optional capabilities

| Answer | Default and condition | Effect |
| --- | --- | --- |
| `use_docs` | True | Adds Sphinx, Furo, Autosummary, API coverage, build scripts, and `docs/` |
| `use_notebooks` | True for data-science projects; false otherwise | Adds exploratory notebooks, JupyterLab, and notebook validation; documentation notebooks require docs too |
| `use_dvc` | False; asked only for data science | Adds `.dvc/`, `.dvcignore`, `dvc.yaml`, dependencies, and a Tox environment |
| `use_uml` | False; asked only with docs | Adds Pyreverse, Mermaid rendering, diagram sources, and `uml` |
| `use_example_gallery` | False; asked only with docs | Adds Sphinx-Gallery, Matplotlib, and executable examples |
| `use_precommit` | True | Adds hooks and the `pre-commit` and `repo-checks` Tox environments |
| `use_vscode` | True | Adds shared formatting, testing, and extension settings |
| `ci_provider` | GitHub Actions | Renders GitHub Actions, GitLab CI, Bitbucket Pipelines, or no CI file |
| `has_other_contributors` | False | Adds provider-native ownership and contribution templates plus a code of conduct |
| `code_owners` | Required when other contributors are enabled | Space-separated provider-native users, teams, groups, or emails placed in `CODEOWNERS` |

Collaboration paths follow the selected provider:

| Provider | Ownership | Change template | Bug-report guidance |
| --- | --- | --- | --- |
| GitHub | `.github/CODEOWNERS` | `.github/PULL_REQUEST_TEMPLATE.md` | `.github/ISSUE_TEMPLATE/bug_report.yml` |
| GitLab | `.gitlab/CODEOWNERS` | `.gitlab/merge_request_templates/Default.md` | `.gitlab/issue_templates/Bug.md` |
| Bitbucket | `.bitbucket/CODEOWNERS` | `.bitbucket/pull_request_template.md` | Checklist in `CONTRIBUTING.md` |
| None | No provider ownership file | No provider template | Checklist in `CONTRIBUTING.md` |

`CODE_OF_CONDUCT.md` is common to every collaboration-enabled project. The template does not configure remote approval or protected-branch settings.

## Project-kind behavior

### Library

The default layout contains a typed import package and starter API. It does not define a console script.

### Application

The application layout adds a console script named after `distribution_name`:

```text
[project.scripts]
<distribution_name> = "<package_name>.main:main"
```

The remainder of the packaging, testing, and validation model stays aligned with library projects.

### Data science

Data-science projects add:

```text
configs/
data/{external,interim,processed,raw}/
models/
references/
reports/
tests/data/
```

They also add `pytest-datadir` and enable NumPy/import-convention Ruff rules. DVC remains a separate choice; selecting the data-science kind does not configure a storage remote.

## Feature interactions

- Notebooks work without Sphinx; documentation notebooks exist only when both features are enabled.
- UML and Sphinx-Gallery require documentation.
- DVC is available only for data-science projects.
- The generated licence is MIT and is not currently a Copier question.
- Exactly one CI provider file is rendered.
- `.copier-answers.yml`, `CONTRIBUTING.md`, and `MAINTAINING.md` are always present.
- `renovate.json` is always present and covers every dependency manager Renovate detects, including weekly lock-file maintenance, but remains inactive until Renovate is enabled on the repository host.
- Collaboration files are absent unless `has_other_contributors` is enabled.
- Conditional files are excluded by Copier rather than copied as inactive scaffolding.

## Fully enabled layout

```text
.
├── .copier-answers.yml
├── .dvc/                           # optional DVC
├── .dvcignore                      # optional DVC
├── .editorconfig
├── .github/                        # provider-specific CI/collaboration alternative
│   ├── CODEOWNERS                  # optional contributors
│   ├── ISSUE_TEMPLATE/             # optional contributors
│   ├── PULL_REQUEST_TEMPLATE.md    # optional contributors
│   └── workflows/ci.yml
├── .gitignore
├── .pre-commit-config.yaml         # optional
├── .python-version
├── .vscode/                        # optional
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md              # optional contributors
├── LICENSE
├── MAINTAINING.md
├── README.md
├── configs/                        # data science
├── data/                           # data science
├── docs/                           # optional Sphinx
│   ├── Makefile
│   ├── README.md
│   ├── make.bat
│   └── source/
│       ├── _templates/autosummary/
│       ├── diagrams/               # optional UML
│       ├── notebooks/              # optional notebooks
│       ├── api.rst
│       ├── conf.py
│       ├── index.md
│       └── readme.md
├── dvc.yaml                        # optional DVC
├── examples/                       # optional Sphinx-Gallery
├── models/                         # data science
├── notebooks/                      # optional
├── pyproject.toml
├── renovate.json                   # optional bot activation
├── references/                     # data science
├── reports/                        # generated reports
├── scripts/
│   ├── build_docs.py               # optional
│   ├── check_notebooks.py          # optional
│   ├── check_package.py
│   ├── clean.py
│   ├── generate_uml.py             # optional
│   └── init_project.py
├── src/<package_name>/
├── tests/
├── tox.ini
└── uv.lock                         # created during initialisation
```

## Stable report paths

| Output | Path |
| --- | --- |
| pytest HTML | `reports/pytest/report.html` |
| pytest JSONL | `reports/pytest/report.jsonl` |
| pytest application log | `reports/pytest/logs/pytest.log` |
| Coverage HTML | `reports/coverage/html/index.html` |
| Coverage XML | `reports/coverage/coverage.xml` |
| Coverage JSON | `reports/coverage/coverage.json` |
| Sphinx HTML | `reports/sphinx/html/index.html` |
| API coverage HTML | `reports/sphinx/coverage/index.html` |
| Raw API coverage | `reports/sphinx/coverage/python.txt` |

Generated reports, build output, virtual environments, caches, generated Autosummary pages, generated gallery pages, and generated Mermaid sources are ignored by Git.
