# Publishing the template documentation

The template manual is a provider-neutral Sphinx site built directly from the authored Markdown files under `docs/`. GitHub Pages is the initial publication target for this repository; it does not change the documentation or CI generated for user projects.

## Build contract

Install the locked template and documentation dependencies, then run the strict HTML build:

```bash
uv sync --locked --group docs
uv run --locked --group docs sphinx-build \
  -W --keep-going \
  -b html \
  docs \
  reports/sphinx/html
```

The build treats warnings as errors and writes a self-contained static site to `reports/sphinx/html/`. Open `reports/sphinx/html/index.html` directly or serve the directory for local review:

```bash
uv run --locked python -m http.server \
  --directory reports/sphinx/html \
  8000
```

The same Sphinx command runs in pull-request validation, the default-branch CI build, and the publication workflow. Provider configuration does not redefine documentation policy.

## GitHub Pages

`.github/workflows/docs-pages.yml` builds the site after a push to `main` or a manual workflow dispatch. It uploads only `reports/sphinx/html/`, then deploys that static artefact through the protected `github-pages` environment.

Before the first deployment, configure the repository once:

1. Open **Settings → Pages** in GitHub.
2. Select **GitHub Actions** as the build and deployment source.
3. Push to `main` or run **Publish template documentation** manually.
4. Follow the deployment URL shown in the workflow summary.

The workflow uses the repository-provided `GITHUB_TOKEN` permissions for Pages. It requires no separately managed API token or publishing branch.

The build job grants `contents: read` for checkout and `pages: read` for the Pages metadata queried by `actions/configure-pages`. The deployment job separately grants `pages: write` and `id-token: write`. Do not add `enablement: true` to `actions/configure-pages` with the default `GITHUB_TOKEN`: automatic enablement requires a separate token with repository administration and Pages write permissions. Keep enablement as the explicit one-time repository setting above.

## Other CI providers

The portable interface is the Sphinx build command and its `reports/sphinx/html/` output:

- GitLab CI can build the same directory and expose it through GitLab Pages.
- Bitbucket Pipelines can retain the directory as an artefact or send it to a chosen static-site host.
- A self-hosted runner can publish the directory to any ordinary static web server or object store.

Only the final upload or deployment step is provider-specific. Keep content, warnings, navigation, and dependency versions in the repository-level Sphinx configuration.

## Documentation ownership

The three documentation sites intentionally serve different scopes:

| Site | Scope |
| --- | --- |
| Template Sphinx site | Complete reference across every Copier option and generated command |
| Generated-project Sphinx site | Project-specific reference rendered from the selected options |
| Full showcase Sphinx site | Executable workflows, fixture values, and expected outputs |

See [Command reference](command-reference.md) for local build commands and [CI and collaboration](ci-and-collaboration.md) for the provider-neutral validation boundary.

## Troubleshooting publication

Reproduce a failed Pages build locally with the strict command before changing the workflow. Common failures are a missing `toctree` entry, a broken document reference, malformed MyST syntax, or an unresolved dependency lock. The previous Pages deployment remains separate from the new build attempt; do not bypass Sphinx warnings to force publication.

If `actions/configure-pages` reports `Resource not accessible by integration`, verify that the build job still has `pages: read`. If it reports that no Pages site exists, complete the one-time **Settings → Pages → GitHub Actions** selection before rerunning the workflow.
