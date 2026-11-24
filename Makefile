# Makefile for the project. Run `make help` to list the targets.

# Name of the conda environment, read from environment.yml so that it is
# defined in one place only.
ENV_NAME := $(shell sed -n 's/^name:[[:space:]]*\([^[:space:]]*\).*/\1/p' environment.yml)

.PHONY: help env test

## help: list the targets of this Makefile
help:
	@sed -n 's/^## //p' $(MAKEFILE_LIST)

## env: create the conda environment, or update it when it exists
env:
	conda env update --name $(ENV_NAME) --file environment.yml --prune

# Run pytest inside the environment without activating it. pytest reads its
# settings from pyproject.toml.
## test: run the unit tests in tests/
test:
	conda run --no-capture-output --name $(ENV_NAME) python -m pytest

# Download the raw Calls for Service file, then rebuild the 2021-2025 table
# from it. This target needs the internet; data/ is a folder, so the target
# is phony.
.PHONY: data
## data: download the raw Calls for Service file and rebuild its table
data:
	conda run --no-capture-output --name $(ENV_NAME) python scripts/download_calls.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_calls.py
