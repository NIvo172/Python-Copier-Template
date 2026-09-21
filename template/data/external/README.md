# External data

Reference or lookup datasets that are *not* produced by the project's own
pipeline — for example a lookup table, a gazetteer, or a static benchmark.
Store small copies here; use the `.dvc` remote for anything too large for Git.
Document the source and download date in the DVC stage that materialises the
file, so provenance is preserved.
