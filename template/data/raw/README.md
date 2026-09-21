# Raw data

Unmodified data exactly as received from its source. Never edit files here.
Clean, normalise, or enrich through DVC stages in `dvc.yaml`, writing the
results to `data/interim` or `data/processed`. Use the `.dvc` remote to
store anything that does not fit under Git LFS limits.
