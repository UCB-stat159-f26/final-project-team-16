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

# Check the code with ruff: lint rules first, then the format. ruff reads its
# settings from pyproject.toml and also checks the notebooks.
.PHONY: lint
## lint: check code style, names, and docstrings with ruff
lint:
	conda run --no-capture-output --name $(ENV_NAME) ruff check .
	conda run --no-capture-output --name $(ENV_NAME) ruff format --check .

# Run pytest inside the environment without activating it. pytest reads its
# settings from pyproject.toml.
## test: run the unit tests in tests/
test:
	conda run --no-capture-output --name $(ENV_NAME) python -m pytest

# Download the raw Calls for Service and crime cases files, then rebuild the
# 2021-2025 tables from them. This target needs the internet; data/ is a
# folder, so the target is phony.
.PHONY: data
## data: download the raw Calls for Service and crime files and rebuild their tables
data:
	conda run --no-capture-output --name $(ENV_NAME) python scripts/download_calls.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_calls.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/download_crime_cases.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_crime_cases.py
