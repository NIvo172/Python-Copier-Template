# Processed data

Final, modelling-ready representations of `data/raw` suitable for training,
inference, or evaluation. Files here should be stable, column-documented, and
reproducible through a `dvc.yaml` stage. Models in `models/` are trained
against these files, not against anything in `data/raw` directly.
