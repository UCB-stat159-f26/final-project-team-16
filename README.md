# The rhythm of a college town

[![tests](https://github.com/UCB-stat159-f26/final-project-team-16/actions/workflows/tests.yml/badge.svg)](https://github.com/UCB-stat159-f26/final-project-team-16/actions/workflows/tests.yml)

When and where do problems arise in Berkeley, and does police enforcement follow them?

This repository holds the final project of Team 16 for STAT 159 at UC Berkeley, Fall 2026. The project uses open data from the [Berkeley Police Department Transparency Hub](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/search).

## Team

- Minchee Yang
- John Hu
- Winny Wen

## Research questions

The analysis has four sections. Each section answers a group of related questions.

| Section | Question |
|---|---|
| Context | How have traffic stops and collisions changed over time, and do they move together? |
| Time | At what times of day and days of the week do noise complaints, assaults, and collisions peak? |
| Time | How do the timing patterns of calls for service and police stops differ across types of calls and stops? |
| Time | Do traffic stops happen at the same times as collisions, and does this differ between weekdays and weekends? |
| Academic calendar | Do noise complaints and assaults near campus follow the academic calendar (semester vs. breaks) more than in the rest of Berkeley? |
| Academic calendar | Do noise complaints, assaults, and alcohol-related collisions increase during events like home football games, move-in week, Halloween, and finals? |
| Location | Do areas with more reckless-driving complaints also have more collisions and more traffic stops? |
| Location | Are noise complaints concentrated in a few blocks, and do the same blocks stay hotspots over time? |

## Getting started

You need conda (for example from [Miniforge](https://github.com/conda-forge/miniforge)), `make`, and `git`. On Windows, use WSL and install Miniforge inside it, because `make` is not part of Windows. If `make` is missing in WSL, install it with `sudo apt install make`.

If a new terminal cannot find `conda`, run `conda init` once with the full path and the name of your shell, then open a new terminal. For example, run `~/miniforge3/bin/conda init zsh` on macOS, or `~/miniforge3/bin/conda init bash` on Linux and WSL.

```bash
git clone https://github.com/UCB-stat159-f26/final-project-team-16.git
cd final-project-team-16
make env
conda activate bpd-rhythm
```

`make env` creates the conda environment `bpd-rhythm` from `environment.yml`. If the environment already exists, the same command updates it to match the file. Run `make help` to list all targets.

### Running the tests

```bash
make test
```

`make test` runs `python -m pytest` inside the `bpd-rhythm` environment. pytest reads its settings from `pyproject.toml`, runs the tests in `tests/`, and treats every warning as an error.

### Checking the code

```bash
make lint
```

`make lint` runs `ruff check .` and then `ruff format --check .` inside the `bpd-rhythm` environment. The first command checks code style, import order, names, and docstrings in the NumPy style. The second command lists the files that `ruff format` would change. Both commands read their settings from `pyproject.toml` and also check the notebooks. To format a file, run `ruff format <file>` in the activated environment.
