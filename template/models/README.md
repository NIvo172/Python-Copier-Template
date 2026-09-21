# Models

Trained model artefacts (weights, pickles, ONNX, ONNX-optimized shapes, etc.)
produced by a `dvc.yaml` stage. Do not edit files here by hand; regenerate
them with `uv run dvc repro`. Use the `.dvc` remote to share models across
developers and CI; never commit raw binary files directly to Git.
