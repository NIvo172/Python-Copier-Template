# Documentation

This directory is the complete manual for the Python Project Copier Template. The root `README.md` remains the short repository landing page; [`index.md`](index.md) is the published Sphinx landing page. The guides here explain how to select options, generate and maintain projects, extend the template, and operate every optional feature.

## Choose a reading path

| Goal | Start here | Continue with |
| --- | --- | --- |
| Generate a first project | [Getting started](getting-started.md) | [Template options](template-options.md) |
| Understand a generated repository | [Getting started](getting-started.md) | [Architecture](architecture.md) and [command reference](command-reference.md) |
| Select or change template features | [Template options](template-options.md) | [Updates and releases](updates-and-releases.md) |
| Develop the template itself | [Maintenance](maintenance.md) | [Architecture](architecture.md) |
| Configure CI and collaboration | [CI and collaboration](ci-and-collaboration.md) | [Architecture](architecture.md) |
| Work with data science and DVC | [Data science and DVC](data-science.md) | [Full showcase](maintenance.md#full-data-science-showcase) |
| Update a generated project | [Updates and releases](updates-and-releases.md) | [Troubleshooting](troubleshooting.md) |
| Diagnose a failure | [Troubleshooting](troubleshooting.md) | [Command reference](command-reference.md) |
| Build or publish this manual | [Publishing](publishing.md) | [Command reference](command-reference.md) |

## Guide index

### Tutorials

- [Getting started](getting-started.md) walks from a template checkout to a clean, tagged, validated generated project and then through the first contributor change.
- [Data science and DVC](data-science.md) explains the data layout, pipeline contracts, metrics, plots, provenance, experiments, and storage boundaries.

### Reference

- [Sphinx site index](index.md) defines the published navigation for the complete template manual.
- [Template options](template-options.md) documents every Copier answer, validation rule, conditional interaction, and rendered path.
- [Architecture](architecture.md) defines responsibility boundaries between Copier, `uv`, Tox, package tools, documentation, CI, collaboration, DVC, and Renovate.
- [Command reference](command-reference.md) lists supported template and generated-project commands, when to use them, and their side effects.
- [CI and collaboration](ci-and-collaboration.md) maps provider files, jobs, artefacts, ownership, contribution templates, remote settings, and dependency automation.

### Operations

- [Maintenance](maintenance.md) covers template development, initialisation behavior, source ownership, and validation levels.
- [Updates and releases](updates-and-releases.md) covers Copier upgrades, migrations, dependency updates, version derivation, tagging, and the deliberately manual release boundary.
- [Publishing](publishing.md) defines the strict provider-neutral Sphinx build, GitHub Pages adapter, and publication recovery process.
- [Troubleshooting](troubleshooting.md) provides symptom-oriented recovery procedures that preserve project state.

## Template documentation versus generated documentation

This manual documents the **template repository**. Every generated project receives its own audience-specific documentation:

| Generated file | Audience | Scope |
| --- | --- | --- |
| `README.md` | Users and evaluators | Requirements, installation, usage, project links, and high-level development entry points |
| `CONTRIBUTING.md` | Contributors | Checkout setup, dependencies, tests, reports, coding rules, and optional feature workflows |
| `MAINTAINING.md` | Maintainers | First bootstrap, lock/version policy, CI, builds, collaboration, DVC storage, and Copier updates |
| `docs/README.md` | Documentation authors | Sphinx pages, API reference, examples, notebooks, UML, generated output, and documentation troubleshooting |
| `docs/source/command-reference.md` | Contributors and maintainers | Project-specific commands rendered only for selected Copier features |
| `CODE_OF_CONDUCT.md` | Project community | Participation and enforcement expectations when collaboration support is enabled |

Generated documentation is conditional. For example, DVC instructions appear only for a data-science project with DVC enabled, and provider-specific instructions name only the selected CI provider.

The companion full data-science showcase publishes the generated command reference unchanged, then adds walkthroughs that execute every optional workflow and identify the expected reports, packages, metrics, plots, and provenance artefacts.

## Sources of truth

Documentation describes behavior; these files enforce it:

| Concern | Source of truth |
| --- | --- |
| Questions, defaults, validation, and exclusions | `copier.yml` |
| Generated files | `template/` |
| Python dependencies and template test tools | `pyproject.toml` and `uv.lock` |
| Template documentation navigation and build | `docs/index.md` and `docs/conf.py` |
| GitHub Pages publication adapter | `.github/workflows/docs-pages.yml` |
| Generated dependency policy | `template/pyproject.toml.jinja` |
| Generated task interface | `template/tox.ini.jinja` |
| Generated project-specific command reference | `template/docs/source/command-reference.md.jinja` |
| Full-feature example | Companion `full-data-science-showcase` repository |
| Structural, migration, and lifecycle contracts | `tests/` |

When documentation and implementation disagree, fix both in the same change and extend a regression test when the behavior is important.

## Documentation maintenance checklist

When a Copier question or generated feature changes:

1. update `copier.yml` and the relevant file under `template/`;
2. update [Template options](template-options.md);
3. update the relevant architecture or operations guide;
4. update conditional generated documentation;
5. update structural tests and notify the showcase repository when its checked-in example should change;
6. render representative configurations;
7. run the template tests, Ruff, and the strict Sphinx build; and
8. run the opt-in normal-project lifecycle for changes that affect initialisation, packaging, or generated-project maintenance.
