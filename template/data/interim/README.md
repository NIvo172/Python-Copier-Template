# Interim data

Intermediate artefacts produced by a pipeline stage from `data/raw` and not
yet in their final modelling-ready form. Each file here should be reproducible
by `uv run dvc repro`. Commit only small, deterministic derivatives; push
large intermediates through the `.dvc` remote.
