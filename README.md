# The rhythm of a college town

[![tests](https://github.com/UCB-stat159-f26/final-project-team-16/actions/workflows/tests.yml/badge.svg)](https://github.com/UCB-stat159-f26/final-project-team-16/actions/workflows/tests.yml)
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/UCB-stat159-f26/final-project-team-16/HEAD?labpath=main.ipynb)

When and where do problems arise in Berkeley, and does police enforcement follow them?

This repository holds the data, code, analysis notebooks, and report for Team 16's STAT 159 final project at UC Berkeley, Fall 2026. We use four open datasets from the [Berkeley Police Department (BPD) Transparency Hub](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/search): calls for service, crime cases, traffic collisions, and vehicle stops. We describe when and where noise complaints, assaults, collisions, and reckless-driving complaints are recorded and compare them with vehicle stops.

- **Website:** <https://ucb-stat159-f26.github.io/final-project-team-16/> has the main report and every analysis notebook.
- **Main report:** [`main.ipynb`](main.ipynb) summarizes and discusses the results.
- **Run it online:** the Binder badge above opens `main.ipynb` in JupyterLab with nothing to install. Binder builds the `bpd-rhythm` environment from `environment.yml`, and the first start can take several minutes.

## Motivation

Berkeley is a city built around a large university. Daily life follows the hour of the day, the day of the week, and the academic calendar. Parties, football games, move-in, and finals change who is in town and what they do. BPD publishes its records as open data, so anyone can check if these rhythms appear. Calls for service, crime cases, and collisions describe demand: what residents report and police record. Vehicle stops describe a response officers start themselves. Comparing their timing and place shows how far enforcement lines up with reported problems. The results are descriptive summaries of recorded events. We make no claim about the effect of enforcement.

## Team

- Minchee Yang
- John Hu
- Winny Wen

## Research questions and analysis

Our analysis is organized into four sections: context, time, academic calendar, and location. Each section answers a group of related questions, and each question has an ID used across the notebooks and the report.

| Section | Question | Notebook | Datasets |
|---|---|---|---|
| Context | A1. How have traffic stops and collisions changed over time, and do they move together? | [`02_trends.ipynb`](notebooks/02_trends.ipynb) | Stops, collisions |
| Time | A2. At what times of day and days of the week do noise complaints, assaults, and collisions peak? | [`03_clock.ipynb`](notebooks/03_clock.ipynb) | Calls, crime cases, collisions |
| Time | A6. How do the timing patterns of calls for service and police stops differ across types of calls and stops? | [`03_clock.ipynb`](notebooks/03_clock.ipynb) | Calls, stops |
| Time | A7. Do traffic stops happen at the same times as collisions, and does this differ between weekdays and weekends? | [`03_clock.ipynb`](notebooks/03_clock.ipynb) | Stops, collisions |
| Academic calendar | A3. Do noise complaints and assaults near campus follow the academic calendar (semester vs. breaks) more than in the rest of Berkeley? | [`04_calendar.ipynb`](notebooks/04_calendar.ipynb) | Calls, crime cases |
| Academic calendar | A4. Do noise complaints, assaults, and alcohol-related collisions increase during events like home football games, move-in week, Halloween, and finals? | [`04_calendar.ipynb`](notebooks/04_calendar.ipynb) | Calls, crime cases, collisions |
| Location | A5. Do areas with more reckless-driving complaints also have more collisions and more traffic stops? | [`06_driving_places.ipynb`](notebooks/06_driving_places.ipynb) | Calls, collisions, stops |
| Location | A8. Are noise complaints concentrated in a few blocks, and do the same blocks stay hotspots over time? | [`05_noise_hotspots.ipynb`](notebooks/05_noise_hotspots.ipynb) | Calls |

Every notebook works with counts of recorded events. `01_data_overview.ipynb` checks table contents and time reliability first. The trends notebook correlates monthly stops and collisions (Pearson and Spearman). The clock notebook builds 24-hour share profiles, measures overlap from 0 to 1, and runs a fixed-seed permutation test with 9,999 shuffles. The calendar notebook compares Fall 2024 semester and winter break daily rates by area, plus event days with matched ordinary days. The location notebooks rank the 14 police beats with Spearman correlation and measure the share of noise calls in the busiest blocks. Each notebook saves its result tables, four of them also save figures, and `main.ipynb` reports them.

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

### Rerunning the analysis

```bash
make all
```

`make all` runs every notebook in `notebooks/` in name order, followed by `main.ipynb` and `contributions.ipynb`, inside the `bpd-rhythm` environment. Each notebook runs in place with the `python3` kernel and rewrites its figures in `figures/` and its tables in `results/`. The command reads only files in the repository and does not download data. Run times are not saved in the notebooks, so a second run produces the same files.
