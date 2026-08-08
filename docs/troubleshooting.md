# Troubleshooting

Start with the terminal output from `init_project.py` for bootstrap failures and the first failing Tox environment for validation failures. Preserve the worktree while diagnosing; the project scripts intentionally do not discard source changes.

## `uv` or Git is missing

The generated initialisation script checks both commands before changing project state. Install the missing executable, confirm it is on `PATH`, and rerun the same initialisation command.

## Version discovery fails before the initial tag

Run the generated initialisation script instead of installing or building an uninitialised project directly. The script creates Git history and the first tag before final synchronisation.

## The initial tag exists on another commit

Initialisation refuses to move a tag. Inspect repository state:

```bash
git status
git log --oneline --decorate -5
git show-ref --tags
```

Resume an unfinished bootstrap only when the requested tag is absent or already points to `HEAD`. Do not rerun initialisation as routine maintenance.

## Pre-commit fails during initialisation

Initialisation retries only while hooks modify files and stops after three attempts. Use the terminal output, run the hooks directly, and inspect changes:

```bash
uv run pre-commit run --all-files --show-diff-on-failure
git status --short
```

If a hook fails without modifying files, correct the reported problem before resuming.

## Initialisation leaves a dirty worktree

A dirty result means a non-ignored file changed:

```bash
git status --short
```

Review formatter, DVC, generated documentation, and manual changes. Initialisation deliberately does not discard them.

## A Python Tox environment cannot start

List configured environments and available interpreters:

```bash
uv run tox list
uv python list
```

Then run one environment directly:

```bash
uv run --locked tox run -e py311
```

The default Tox suite tests the minimum version. `tox run -m test` requests every selected version.

## The lock check fails

If the dependency change is intentional:

```bash
uv lock
uv sync
uv run --locked tox run -e lock
```

Commit `pyproject.toml` and `uv.lock` together.

## DVC reports stale output

```bash
uv run dvc status
uv run dvc repro
git status --short
```

The template does not configure a storage remote. Add one separately when shared data/model storage is required.

## DVC remote authentication fails

Inspect the configured remote without printing credentials:

```bash
uv run dvc remote list
uv run dvc config core.remote
```

Keep shareable remote location settings in `.dvc/config` and credentials in the provider credential chain, environment, CI secret store, or an uncommitted local DVC config. Do not paste credential-bearing URLs into logs or issue reports.

## Documentation fails on a warning

The build uses `--fail-on-warning`. Fix the first warning and rerun the same target. For incomplete public API documentation, inspect `reports/sphinx/coverage/index.html`.

## Copier cannot find the template

Inspect `_src_path` and `_commit` in `.copier-answers.yml` without editing them. Make the recorded local path or remote reachable, clean the generated worktree, fetch the desired tag, and retry with `--pretend`.

## Copier proposes unexpected deletions

Stop before applying the update and preview a concrete template tag:

```bash
copier update --pretend --vcs-ref=<template-tag>
```

Confirm the recorded answers still select the relevant optional feature and that the new template has not intentionally changed its exclusion rules. Project-kind, CI-provider, documentation, notebook, DVC, and collaboration changes can legitimately remove conditional files. Back up or commit project-owned content before applying the update.

## Code owners do not receive review requests

Validate the owner tokens and paths using the selected provider's syntax. Then enable code-owner review enforcement or required approvals in the remote repository settings. A checked-in `CODEOWNERS` file identifies owners but does not by itself enable protected branches or approval rules.

## Renovate does not open updates

`renovate.json` configures behavior but does not activate Renovate. Confirm that the Renovate app/service is enabled for the repository or that a self-hosted runner includes it. Then inspect the Renovate dependency dashboard and logs for onboarding, permissions, registry access, or unsupported-file messages.

If `uv.lock` maintenance fails while declaration updates succeed, verify that the Renovate runtime can execute `uv` and access every configured Python package source.

## A required report is missing

Run the environment that owns the report:

| Missing output | Command |
| --- | --- |
| pytest/coverage reports | `uv run --locked tox run -e py<minimum>` |
| Sphinx HTML or API coverage | `uv run --locked tox run -e docs` |
| distributions under `dist/` | `uv run --locked tox run -e package-check` |

Generated output can be removed and rebuilt with `uv run --locked tox run -e clean` followed by the responsible environment.

## CI computes an unexpected version

Version providers need tags and sufficient history:

```bash
git describe --tags --always --dirty
git tag --points-at HEAD
```

Ensure CI uses a full-history checkout and the expected tag exists.
