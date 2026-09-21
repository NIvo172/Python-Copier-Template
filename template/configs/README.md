# Configurations

YAML / TOML / INI files that parameterise pipelines and experiments without
requiring a code change. Add one config per concern (e.g. `configs/experiment.yaml`,
`configs/model-hyperparameters.yaml`) and reference them from `dvc.yaml` stages or
from your training entry point. Do not store secrets here; use the provider
secret store or environment variables for anything credential-bearing.
