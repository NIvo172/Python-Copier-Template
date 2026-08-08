# Template maintenance

This guide covers generated-project initialisation, template development, focused validation, versioning, and Copier updates. The complete release and migration policy is in [Updates and releases](updates-and-releases.md).

## Bootstrap a generated project

Copier prints the exact initialisation command after rendering:

```bash
uv run ../my-project/scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
```

The script contains PEP 723 inline metadata and has no third-party Python dependencies. `uv` can run it before the generated package has Git-derived version metadata.

Available options:

```text
--git-name NAME       repository-local Git author name
--git-email EMAIL     repository-local Git author email
--tag TAG             initial tag; default v0.0.1
```

The script uses `John Doe <john.doe@example.com>` when no Git identity override is supplied. It changes repository-local configuration only.

### Initialisation lifecycle

The script:

1. checks for `git` and `uv`;
2. initialises a `main` branch and local Git identity;
3. creates an initial commit when no `HEAD` exists;
4. runs `uv sync` and creates `uv.lock`;
5. reruns pre-commit while hooks continue changing files, up to three attempts;
6. runs `dvc repro` when `dvc.yaml` declares stages;
7. stabilises hooks again after DVC;
8. commits lock/generated state when necessary;
9. requires a clean worktree;
10. creates the requested tag or verifies that it already points to `HEAD`;
11. synchronises the tag-derived package version; and
12. verifies that the worktree remains clean.

The script removes a foreign `VIRTUAL_ENV` from child commands so an unrelated active environment cannot override the generated `.venv`.

Initialisation can resume many partial first-run failures, but it is not a normal contributor command. The script refuses to move an existing initial tag from another commit. Output is streamed to the terminal and no log file is created.

Run repeatable project validation separately:

```bash
uv run --locked tox
```

## Maintain a generated project

Daily development is documented in generated `CONTRIBUTING.md`. Long-term maintainer operations are documented in generated `MAINTAINING.md`.

Generated projects retain `.copier-answers.yml`. Preview and apply an update from a clean worktree:

```bash
copier update --pretend --vcs-ref=:current:
copier update --vcs-ref=:current:
```

Use a concrete release tag for an intentional template upgrade:

```bash
copier update --vcs-ref=v0.2.0
```

Review conflicts and rendered changes before committing. Do not edit `.copier-answers.yml` manually. Package-name, project-kind, minimum-Python, and build-backend changes should be treated as migrations.

When an answer is renamed, removed, split, or changes meaning, add a versioned migration under `_migrations` in `copier.yml`. Do not add no-op migrations for ordinary template file changes. Migration commands require Copier's trusted-template execution mode and must be small, deterministic, and covered by tests.

The regression suite constructs temporary `v0.1.0` and `v0.2.0` template tags, renders from the older tag, preserves project-owned content, executes a versioned migration, and verifies the updated answers and generated files.

After an update:

```bash
uv lock
uv sync
uv run --locked tox
```

## Automated dependency maintenance

The template repository and every generated project include `renovate.json`. After Renovate is enabled on the selected repository host, it discovers every supported dependency source present in the repository and proposes updates for items such as:

- PEP 621 dependencies and their corresponding `uv.lock` state;
- compatible transitive dependencies through weekly lock-file maintenance;
- pre-commit hooks;
- GitHub Actions, GitLab CI, or Bitbucket Pipelines dependencies selected by the project; and
- container images and additional supported dependency files added later.

Routine minor, patch, pin, and digest updates are grouped, while major upgrades remain separate. Renovate may update dependency references inside CI configuration, but it does not otherwise harden or restructure the CI workflows. Review Renovate changes as ordinary contributions and require the normal locked Tox validation before merging.

## Develop this template

The root environment is intentionally small:

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

Structural tests render:

- Hatchling and Setuptools;
- libraries, applications, and data-science packages;
- Google and NumPy docstrings;
- documentation and notebook combinations;
- DVC, UML, gallery, pre-commit, and VS Code choices;
- GitHub, GitLab, Bitbucket, and no CI; and
- provider-native collaboration paths and their disabled state;
- a tagged Copier update with a versioned migration and project-owned content; and
- the README/contributor/maintainer document boundaries; and
- the template Sphinx navigation and GitHub Pages publication contract.

`RUN_GENERATED_BUILDS=1` enables generated distribution builds:

```bash
RUN_GENERATED_BUILDS=1 uv run pytest
```

The standard suite also renders representative option combinations and checks generated contracts. Run the normal-project integration lifecycle explicitly when changing initialisation, tests, reports, or tag behavior:

```bash
RUN_NORMAL_PROJECT=1 uv run pytest tests/test_generated_projects.py -k normal_project_complete_lifecycle
```

This lifecycle uses the active template-development Python minor version, enables documentation, notebooks, DVC, UML, the example gallery, pre-commit, and VS Code support, and selects no hosted CI provider. It runs `scripts/init_project.py`, then the complete default Tox suite as a separate command, and checks tagging and final repository cleanliness.

## Full data-science showcase

The all-features example is maintained as the separate `full-data-science-showcase` repository. That repository owns its example pipeline, DVC outputs, narrative documentation, integration tests, and exhaustive validation driver. The template repository does not regenerate or test the showcase; this keeps template validation focused on Copier rendering, conditional files, documentation contracts, and updates.

## Template source ownership

| Path | Ownership |
| --- | --- |
| `copier.yml` | Questions, validation, exclusions, and messages |
| `template/` | Generated-project source of truth |
| `template/README.md.jinja` | User-facing generated landing page |
| `template/CONTRIBUTING.md.jinja` | Generated daily development guide |
| `template/MAINTAINING.md.jinja` | Generated bootstrap and maintenance guide |
| `template/docs/README.md.jinja` | Optional documentation-author guide |
| `docs/conf.py` and `docs/index.md` | Provider-neutral template-manual build and navigation |
| `.github/workflows/docs-pages.yml` | GitHub Pages publication adapter for the built template manual |
| `tests/test_documentation.py` | Template-manual navigation, links, anchors, option, command, script, and Tox contracts |
| `tests/test_generated_projects.py` | Rendered feature combinations and generated-documentation references |

Do not use a previously generated project as the source of truth. Changes to feature behavior normally require synchronized edits to `copier.yml`, templates, documentation, and tests.

## Versioning expectations

Generated distributions use Git tags for versions. Template updates are also most reliable when the template itself is a Git repository with PEP 440-compatible release tags.

Generated project initialisation creates `v0.0.1` by default. Builds on that commit receive `0.0.1`; later commits receive development versions until the next tag.
