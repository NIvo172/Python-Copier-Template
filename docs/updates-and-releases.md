# Updates and releases

This guide separates four workflows that are easy to confuse: dependency updates, Copier template updates, generated-project releases, and template releases.

## Workflow summary

| Workflow | Changes | Primary commands | Version/tag effect |
| --- | --- | --- | --- |
| Dependency update | `pyproject.toml`, `uv.lock`, hooks, CI dependency refs, images | `uv add`, `uv lock`, Renovate | No tag automatically created |
| Copier update | Generated files and recorded answers | `copier update` | Moves project to a newer template revision; no project tag automatically created |
| Generated-project release | Package source and metadata | Tox validation, Git tag | Git tag defines the package version |
| Template release | `copier.yml`, `template/`, docs, tests, fixtures | Template validation, Git tag | Provides a stable `--vcs-ref` for generation/update |

## Dependency updates

For intentional manual changes:

```bash
uv add <package>
uv remove <package>
uv lock
uv sync
uv run --locked tox
```

Commit declarations and `uv.lock` together.

Renovate covers all detected managers and weekly lock-file maintenance. Routine minor, patch, pin, and digest changes are grouped; major updates remain separate. Renovate does not automerge by configuration in this template. Review and validate its proposals normally.

## Prepare for a Copier update

Generated projects retain `.copier-answers.yml`, which records the template source, revision, and answers. Do not edit it manually.

Before updating:

```bash
git status --short
git fetch --tags
```

The worktree should be clean. Commit or deliberately stash project-owned changes before allowing Copier to perform its three-way comparison.

Use a concrete template tag whenever possible:

```bash
copier update --pretend --vcs-ref=v1.1.0
```

`--pretend` previews file operations without applying them. Review the selected revision and expected additions/removals.

## Apply a Copier update

```bash
copier update --vcs-ref=v1.1.0
```

Then inspect:

```bash
git status --short
git diff --stat
git diff
```

Resolve conflicts as project decisions, not mechanical acceptance. In particular, review:

- project-owned README and documentation changes;
- dependency declarations and lock state;
- selected/removed optional feature files;
- CI provider changes;
- package/build backend changes; and
- scripts whose generated baseline changed while the project also customized them.

Afterward:

```bash
uv lock
uv sync
uv run --locked tox
uv run --locked tox run -m test
```

Commit the update as a focused change that names the old and new template revisions.

## When a Copier migration is required

Ordinary template file edits do not need migrations. Add a versioned `_migrations` entry to `copier.yml` when an update cannot be represented safely by normal rendering, for example when:

- an answer is renamed or removed;
- one answer is split into several answers;
- an answer's meaning or accepted values change;
- project-owned files must be moved; or
- a structural transformation must happen before/after rendering.

Migration commands must be:

- small and deterministic;
- bounded to the generated project;
- safe to resume or clearly fail;
- associated with a concrete template version; and
- covered by regression tests.

Copier requires trusted-template execution for migrations. Do not put broad environment access, credential handling, network calls, or unrelated system mutations into a migration.

The regression suite renders from a temporary `v0.1.0`, adds project-owned content, updates through a temporary `v0.2.0` migration, and verifies that answers, generated changes, migration output, and project content are all preserved.

## Generated-project version model

Both supported build stacks derive package versions from Git:

| Build choice | Version provider |
| --- | --- |
| Hatchling | `hatch-vcs` |
| Setuptools | `setuptools-scm` |

A clean commit tagged `v1.2.3` builds version `1.2.3`. Commits after that tag build PEP 440 development versions based on repository distance/state.

The one-time initialisation creates `v0.0.1`. Validation is a separate Tox command; later release tags are a maintainer operation.

## Validate a generated-project release

From a clean established repository:

```bash
uv lock --check
uv run --locked tox
uv run --locked tox run -m test
uv run --locked tox run -e package-check
git status --short
```

Run optional feature checks explicitly when they are not part of the default environment list or when release policy requires extra assurance.

Inspect built distributions under `dist/`. The package check already requires an sdist and wheel, runs `twine check --strict`, and validates every wheel with `check-wheel-contents`.

## Create a generated-project release tag

After the release commit has passed validation:

```bash
git tag -a v1.2.3 -m "Release v1.2.3"
git push origin main
git push origin v1.2.3
```

Use the project's chosen signed/annotated-tag policy. The template intentionally does not publish packages, generate release notes, create attestations, or handle package-index API tokens. Add publishing only when the target registry and trust model are understood.

## Release the template

Before tagging the template itself:

```bash
uv sync --locked
uv run pytest
uv run ruff check .
uv run ruff format --check .
RUN_GENERATED_BUILDS=1 uv run pytest
RUN_NORMAL_PROJECT=1 uv run pytest tests/test_generated_projects.py -k normal_project_complete_lifecycle
```

Verify that:

- every new or changed answer is documented;
- conditional exclusions render correctly;
- generated documentation matches feature selections;
- provider variants are covered;
- migrations are versioned and tested;
- the companion showcase remains independent from the template package; and
- the release tag is suitable for Copier's `--vcs-ref`.

Tag and push according to the template repository's release policy. Generated projects can then update using that concrete tag.

## Rollback and recovery

Do not move an already published project or template tag. Correct the source in a new commit and release a new version.

If a Copier update is not yet committed, inspect and restore using normal version-control review. Avoid destructive worktree commands when project-owned edits are mixed with generated changes. If the update is committed, prefer a revert commit or a forward template fix so history remains auditable.

See [Troubleshooting](troubleshooting.md) for specific initialisation, lock, DVC, documentation, Copier-source, and version-discovery failures.
