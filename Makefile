# Makefile for the project. Run `make help` to list the targets.

# Name of the conda environment, read from environment.yml so that it is
# defined in one place only.
ENV_NAME := $(shell sed -n 's/^name:[[:space:]]*\([^[:space:]]*\).*/\1/p' environment.yml)

.PHONY: help env test

# Notebooks that `make all` runs, in this order: the analysis notebooks in
# notebooks/ by name (01, 02, ...), then the main report and the
# contributions. A notebook that does not exist yet is skipped.
NOTEBOOKS := $(sort $(wildcard notebooks/*.ipynb)) $(wildcard main.ipynb contributions.ipynb)

# Run a notebook in place with the python3 kernel. Run times are not saved
# in the notebook, so a rerun on the same machine gives the same files.
NBCONVERT := jupyter nbconvert --to notebook --execute --inplace \
	--ExecutePreprocessor.kernel_name=python3 \
	--ExecutePreprocessor.record_timing=False

# Each notebook is its own phony target, so `make all` runs them one by one
# in the order of NOTEBOOKS and stops at the first notebook that fails. The
# notebooks read only files in the repository and never download data.
.PHONY: all $(NOTEBOOKS)
## all: run every notebook in notebooks/, then main.ipynb and contributions.ipynb
all: $(NOTEBOOKS)

$(NOTEBOOKS):
	conda run --no-capture-output --name $(ENV_NAME) $(NBCONVERT) $@

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
# 2021-2025 tables and the block address to sector lookup from them. This
# target needs the internet; data/ is a folder, so the target is phony.
.PHONY: data
## data: download the raw Calls for Service and crime files and rebuild the tables and lookup
data:
	conda run --no-capture-output --name $(ENV_NAME) python scripts/download_calls.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_calls.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/download_crime_cases.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_crime_cases.py
	conda run --no-capture-output --name $(ENV_NAME) python scripts/prepare_address_sectors.py

# Build the website into _build/html with MyST, the same way the deploy
# workflow does. Open _build/html/index.html, or run `myst start` in the
# activated environment for a live preview. _build/ is a folder that git
# ignores, so the target is phony.
.PHONY: html
## html: build the project website into _build/html
html:
	conda run --no-capture-output --name $(ENV_NAME) myst build --html
