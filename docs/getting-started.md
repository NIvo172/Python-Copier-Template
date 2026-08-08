# Getting started

This tutorial creates a project, performs its one-time initialisation, validates it, and shows the normal contributor workflow afterward.

## 1. Install prerequisites

The template checkout requires:

- Python 3.11 or newer;
- [`uv`](https://docs.astral.sh/uv/getting-started/installation/);
- Git; and
- access to any dependency registries required by the selected features.

Verify the executables:

```bash
python --version
uv --version
git --version
```

The generated project may target Python 3.11 through 3.14. `uv` can install missing managed Python interpreters when they are available for the current platform.

## 2. Prepare the template checkout

From the template repository:

```bash
uv sync --locked
uv run pytest
```

Use `uv sync` without `--locked` only when intentionally refreshing the template's own lock file.

## 3. Render a project

From a local checkout:

```bash
uvx copier copy --vcs-ref HEAD . ../my-project
```

From a tagged remote repository:

```bash
uvx copier copy --vcs-ref v1.0.0 \
  https://example.com/organisation/python-project-template.git \
  my-project
```

Copier asks about identity, URLs, Python support, packaging, project kind, optional tools, CI, and collaboration. See [Template options](template-options.md) for every answer and interaction.

Use a released template tag for reproducible project creation. `HEAD` is convenient while developing the template but may change between renders.

## 4. Run the one-time initialisation

Enter the generated repository and run:

```bash
cd ../my-project
uv run scripts/init_project.py \
  --git-name "Your Name" \
  --git-email "you@example.com"
```

The script uses repository-local Git identity. It does not change the user's global Git configuration.

Initialisation:

1. creates or reuses a `main` Git repository;
2. creates the initial source commit;
3. resolves dependencies and writes `uv.lock`;
4. stabilises pre-commit fixes when enabled;
5. reproduces declared DVC stages when enabled;
6. commits generated state;
7. requires a clean worktree;
8. creates `v0.0.1`; and
9. resynchronises the installed package so its version is derived from the tag.

Output is streamed to the terminal. The script does not create a log file.

Run the repeatable validation contract separately after initialisation:

```bash
uv run --locked tox
```

## 5. Verify the result

```bash
git status --short
git log --oneline --decorate -3
git tag --points-at HEAD
uv run python -c "from importlib.metadata import version; print(version('my-project'))"
```

Expected state:

- `git status --short` is empty;
- `v0.0.1` points at `HEAD`;
- `uv.lock` is committed;
- the installed distribution version is `0.0.1`; and
- the required reports exist under `reports/`.

Replace `my-project` in the metadata command with the selected `distribution_name`.

## 6. Configure the remote repository

The template creates local files but does not create a GitHub, GitLab, or Bitbucket repository. Add the chosen remote and push the branch and initial tag:

```bash
git remote add origin <repository-url>
git push -u origin main
git push origin v0.0.1
```

When collaboration support is enabled, configure branch protection, required approvals, and code-owner enforcement in the remote provider. The checked-in ownership and request-template files do not change remote settings by themselves.

When Renovate is desired, enable the Renovate service or self-hosted runner for the repository. The checked-in `renovate.json` defines update behavior but does not run a bot on its own.

## 7. Use the contributor workflow

For every later checkout:

```bash
git clone <repository-url>
cd my-project
uv sync --locked
```

When pre-commit is enabled:

```bash
uv run pre-commit install
```

Run the default validation suite:

```bash
uv run --locked tox
```

The initialisation script is not part of contributor onboarding and should not be rerun after the repository has been initialised.

## 8. Make a first change

```bash
git switch -c feature/example
# Edit src/ and tests/.
uv run --locked tox run -e lint
uv run --locked tox run -e py311
git status --short
```

Use the configured minimum-version environment instead of `py311` when the project minimum is newer. Run the complete selected Python matrix before a major merge:

```bash
uv run --locked tox run -m test
```

See the generated `CONTRIBUTING.md` for the exact commands applicable to that project's selected options.

## 9. Update from the template later

Start from a clean generated-project worktree:

```bash
copier update --pretend --vcs-ref=v1.1.0
copier update --vcs-ref=v1.1.0
uv lock
uv sync
uv run --locked tox
```

Review additions, removals, and conflicts before committing. See [Updates and releases](updates-and-releases.md) for migrations and release policy.

## Next steps

- Choose features in [Template options](template-options.md).
- Learn the task model in [Architecture](architecture.md).
- Look up exact commands in [Command reference](command-reference.md).
- Configure providers in [CI and collaboration](ci-and-collaboration.md).
- Follow the data workflow in [Data science and DVC](data-science.md).
