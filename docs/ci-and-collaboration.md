# CI and collaboration

This guide explains what the template writes for GitHub, GitLab, and Bitbucket, what remains provider-neutral, and which settings still belong in the remote repository.

The template repository's own GitHub Pages workflow is not copied into generated projects. It publishes the complete template manual; generated-project CI remains controlled solely by the selected `ci_provider` answer.

## Provider selection

The `ci_provider` answer renders exactly one provider configuration:

| Choice | CI file | Collaboration directory |
| --- | --- | --- |
| GitHub Actions | `.github/workflows/ci.yml` | `.github/` |
| GitLab CI/CD | `.gitlab-ci.yml` | `.gitlab/` |
| Bitbucket Pipelines | `bitbucket-pipelines.yml` | `.bitbucket/` |
| None | None | No provider-specific collaboration files |

Unselected provider files are excluded during Copier rendering. They are not copied as dormant examples.

## Shared validation contract

Provider YAML provisions Python and `uv`, then delegates project policy to named Tox environments. This keeps local and hosted validation aligned.

| Validation concern | Tox environment | Typical provider job |
| --- | --- | --- |
| Repository hygiene | `repo-checks` | Repository/pre-commit job |
| Lock consistency | `lock` | Lock job |
| Formatting, linting, typing | `lint` | Lint job |
| Supported Python versions | `pyXY` | Matrix or version-specific jobs |
| Notebook hygiene | `notebooks` | Optional notebook job |
| DVC state | `dvc` | Optional data job |
| Documentation | `docs` | Optional docs job |
| Distribution validation | `package-check` | Package job |

The provider files do not duplicate Ruff, Mypy, pytest, package, DVC, or Sphinx policy. Change those contracts in `pyproject.toml`, `tox.ini`, or the responsible script.

## History and versioning

Generated packages derive versions from Git tags. CI therefore fetches enough history and tags for Hatch VCS or setuptools-scm to compute the intended version.

When a provider reports an unexpected development version, verify:

```bash
git describe --tags --always --dirty
git tag --points-at HEAD
```

Then confirm the provider checkout is not shallow and the expected tag was pushed.

## Artefacts

Where supported, CI retains:

- pytest HTML and JSONL reports;
- coverage HTML, XML, and JSON;
- Sphinx HTML and API-coverage output;
- source distributions and wheels; and
- task-specific output copied into provider artefact directories.

The canonical local report paths are listed in [Template options](template-options.md#stable-report-paths).

## Cancellation behavior

- GitHub Actions cancels superseded runs through workflow concurrency.
- GitLab marks jobs interruptible and allows newer pipelines to supersede work according to provider settings.
- Bitbucket uses the same Tox contract but the generated YAML does not implement repository-level auto-cancel behavior.

These are scheduling behaviors, not validation-policy differences.

## Collaboration switch

`has_other_contributors` controls whether collaboration files are rendered. When enabled, `code_owners` must contain at least one provider-native owner token.

| Provider | Ownership | Change description | Bug report |
| --- | --- | --- | --- |
| GitHub | `.github/CODEOWNERS` | `.github/PULL_REQUEST_TEMPLATE.md` | `.github/ISSUE_TEMPLATE/bug_report.yml` |
| GitLab | `.gitlab/CODEOWNERS` | `.gitlab/merge_request_templates/Default.md` | `.gitlab/issue_templates/Bug.md` |
| Bitbucket | `.bitbucket/CODEOWNERS` | `.bitbucket/pull_request_template.md` | Checklist in `CONTRIBUTING.md` |
| No CI provider | No ownership file | Contributor-guide workflow | Contributor-guide checklist |

Every collaboration-enabled project also receives `CODE_OF_CONDUCT.md`.

## Code-owner values

`code_owners` is inserted as a space-separated owner list for the repository root. Use syntax understood by the selected provider, for example:

```text
@organisation/platform-team @maintainer
```

or provider-supported group/user/email equivalents. The template validates only that the answer is not empty; the remote provider validates whether the identities exist and can be assigned.

Update the generated ownership file when teams or responsibilities change. For complex ownership, add narrower path rules directly to the provider-native file.

## Remote settings are separate

Checked-in files can suggest reviewers and prefill contribution descriptions, but they do not configure remote repository policy. Configure these settings in GitHub, GitLab, or Bitbucket as appropriate:

- protected/default branch;
- required successful CI checks;
- minimum approvals;
- code-owner approval enforcement;
- merge strategy;
- who may push tags or protected branches;
- issue tracker availability; and
- artefact retention limits.

The template intentionally avoids provider API tokens and does not make remote API calls during generation or initialisation.

## Renovate

`renovate.json` is provider-neutral. Once a Renovate app, service, or self-hosted runner is enabled, it discovers every supported dependency manager present in the repository.

The generated policy:

- enables the dependency dashboard;
- enables weekly compatible lock-file maintenance;
- labels updates `dependencies`;
- groups minor, patch, pin, and digest updates as `routine dependencies`; and
- leaves major upgrades separate.

Detected sources may include PEP 621 dependencies, `uv.lock`, pre-commit hooks, GitHub Actions, GitLab/Bitbucket CI dependencies, and container images. Renovate may update dependency references inside CI files, but it does not otherwise redesign jobs, permissions, triggers, or validation policy.

Treat every Renovate proposal as a normal contribution:

```bash
uv sync --locked
uv run --locked tox
uv run --locked tox run -m test
```

## Changing provider later

Change `ci_provider` through Copier rather than copying another provider's sample manually:

```bash
copier update --pretend --vcs-ref=<template-tag>
copier update --vcs-ref=<template-tag>
```

Review removal of the old provider files and addition of the new ones. Then configure secrets, branch rules, required checks, and artefact retention in the new remote provider.

## No-CI projects

Selecting `none` removes provider YAML but keeps all local Tox environments. This is useful for local-only projects or repositories whose automation is managed elsewhere.

Run the complete local contract before merging or releasing:

```bash
uv run --locked tox
uv run --locked tox run -m test
```
