# Data science and DVC

This guide documents the generated data-science layout, the optional DVC contract, and the relationship to the standalone data-science showcase.

## Enable data-science support

Select:

```text
project_kind = data_science
```

This adds data/configuration/report directories and data-science lint/test conventions. DVC remains independent:

```text
use_dvc = true or false
```

Choosing data science does not automatically configure external data storage.

## Directory responsibilities

| Path | Intended contents | Typical Git policy |
| --- | --- | --- |
| `configs/` | Versioned experiment, feature, and model configuration | Commit |
| `data/external/` | Data received from outside systems | Track metadata; usually do not commit large data |
| `data/raw/` | Immutable source snapshots | Track metadata; usually DVC/remote storage |
| `data/interim/` | Reproducible intermediate data | Regenerate or track with DVC when expensive |
| `data/processed/` | Analysis/model-ready data | Regenerate or track with DVC |
| `models/` | Model artefacts or model metadata | DVC/remote storage for large binaries |
| `references/` | Data dictionaries and supporting domain references | Commit |
| `reports/` | Metrics, figures, tables, and generated validation output | Commit only intentional authored artefacts |
| `notebooks/` | Exploratory analysis when notebooks are enabled | Commit stripped, reproducible notebooks |
| `tests/data/` | Small deterministic test fixtures | Commit |

Project-specific policy may differ, but each directory should have one documented ownership and retention rule.

## Configuration policy

Keep reusable parameters in versioned files under `configs/`. A pipeline parameter is meaningful only when:

1. the stage declares it;
2. the command or imported configuration consumes it;
3. the output changes when the parameter changes; and
4. a test verifies important semantics.

Do not add decorative parameters that are declared in `dvc.yaml` but ignored by the implementation.

## DVC repository boundary

When DVC is enabled, the project contains:

- `.dvc/config` for shared non-secret remote configuration;
- `.dvc/.gitignore` and `.dvcignore`;
- `dvc.yaml` for stage declarations; and
- `dvc.lock` after the first successful reproduction.

The initialisation script runs `dvc repro` and commits resulting DVC metadata and generated ignore rules. The separate Tox validation verifies `dvc status`.

## Stage contract

A complete stage should make dependencies, parameters, outputs, metrics, and plot data explicit:

```yaml
vars:
  - configs/models/baseline.yaml

stages:
  prepare-example-data:
    cmd: >-
      python -m example.pipeline
      tests/data/observations.csv
      data/processed/summary.json
      data/processed/metrics.json
      reports/figures/cumulative_mean.csv
      --round-digits ${summary.round_digits}
    deps:
      - src/example/pipeline.py
      - tests/data/observations.csv
    params:
      - configs/models/baseline.yaml:
          - summary.round_digits
    outs:
      - data/processed/summary.json
    metrics:
      - data/processed/metrics.json
    plots:
      - reports/figures/cumulative_mean.csv:
          x: observation
          y: cumulative_mean
```

Use:

- `deps` for code and input data that invalidate the stage;
- `params` for versioned behavioral configuration;
- `outs` for reproducible non-metric artefacts;
- `metrics` for scalar machine-readable results; and
- `plots` for comparison series with stable axes.

## Determinism and provenance

Pipeline summaries should include enough stable provenance to identify their inputs and configuration. Prefer content-derived values such as SHA-256 digests over:

- absolute filesystem paths;
- host names;
- local timestamps;
- temporary directory names; or
- process-specific identifiers.

Tests should assert deterministic outputs for a small committed fixture. The companion showcase records:

- mean and record count;
- configured rounding precision;
- the SHA-256 digest of the input CSV; and
- a cumulative-mean series for plotting.

## Daily DVC workflow

After changing code, data, or configuration:

```bash
uv run dvc status
uv run dvc repro
uv run dvc metrics show
uv run dvc plots show
git status --short
```

Commit:

- changed code/configuration;
- `dvc.yaml` when the stage contract changes;
- `dvc.lock` when reproduced state changes;
- generated DVC `.gitignore` rules; and
- intentionally versioned small reports or metadata.

Do not commit large files that DVC has placed under ignore rules.

## Experiments

When parameters, metrics, and plots are declared, run experiments with:

```bash
uv run dvc exp run
uv run dvc exp show
```

Experiments are useful only when the declared outputs support meaningful comparison. Keep experiment names and configuration changes interpretable, and promote important results into normal Git/DVC history according to project policy.

## Configure remote storage

No remote is generated because storage choice and credentials are infrastructure-specific.

```bash
uv run dvc remote add -d storage <remote-url>
uv run dvc push
```

Commit `.dvc/config` only when it contains shareable, non-secret settings. Store credentials in the provider's credential chain, environment, secret store, or CI secret mechanism. Never commit tokens, passwords, access keys, or credential-bearing URLs.

New contributors retrieve tracked objects with:

```bash
uv sync --locked
uv run dvc pull
uv run --locked tox run -e dvc
```

## Notebook policy

Exploratory notebooks under `notebooks/` are checked recursively. Removable output and volatile execution metadata must be stripped unless a cell explicitly opts into retained output through the supported metadata/tag convention.

Documentation notebooks under `docs/source/notebooks/` are authored pages and follow the documentation policy instead. Their execution is disabled during Sphinx builds, so committed content must be intentional and stable.

## Full data-science showcase

The companion `full-data-science-showcase` repository is a checked-in project that demonstrates:

- every optional Copier capability;
- provider-native collaboration files;
- a parameter consumed by real pipeline code;
- DVC outputs, metrics, and plot data;
- content-based input provenance;
- unit and CLI-level pipeline tests; and
- an executable exhaustive check of the Python matrix, hooks, documentation targets, UML, DVC commands, packages, reports, and clean-worktree invariant.

It is maintained independently and does not require a generator or fixture overlay from this template repository.
