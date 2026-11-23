# Makefile for the project. Run `make help` to list the targets.

# Name of the conda environment, read from environment.yml so that it is
# defined in one place only.
ENV_NAME := $(shell sed -n 's/^name:[[:space:]]*\([^[:space:]]*\).*/\1/p' environment.yml)

.PHONY: help env

## help: list the targets of this Makefile
help:
	@sed -n 's/^## //p' $(MAKEFILE_LIST)

## env: create the conda environment, or update it when it exists
env:
	conda env update --name $(ENV_NAME) --file environment.yml --prune
