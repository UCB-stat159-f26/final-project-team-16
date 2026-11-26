---
title: The rhythm of a college town
short_title: Home
subtitle: When and where do problems arise in Berkeley, and does police enforcement follow them?
site:
  hide_outline: true
---

:::{aside}
:class: meta
**Course**
STAT 159, UC Berkeley, Fall 2026

**Data**
[Berkeley Police Department Transparency Hub](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/search)

**Tables**
Calls for service, crime cases, collisions, and vehicle stops

**Run it online**
[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/UCB-stat159-f26/final-project-team-16/HEAD?labpath=main.ipynb)
:::

:::{div}
:class: lead
This is the final project of Team 16 for STAT 159. It uses four tables of open data from the Berkeley Police Department and asks four groups of questions: the context, the time of day and week, the academic calendar, and the location. The [main report](main.ipynb) tells the whole story.
:::

::::{div}
:class: glance
:::{div}
:class: tile
**307,628**

calls for service, 2021 to 2025
:::
:::{div}
:class: tile
**51,418**

crime cases, 2021 to 2025
:::
:::{div}
:class: tile
**16,639**

collisions, Dec 2007 to Nov 2026
:::
:::{div}
:class: tile
**7,431**

vehicle stops, Jan 2024 to May 2026
:::
::::

:::{div}
:class: small
Records in each processed table, from the [data overview](notebooks/01_data_overview.ipynb).
:::

## Three rhythms in one day

Noise calls peak at 23:00, when 17.2% of them come in. Assault cases peak at noon and collisions at 17:00.

:::{figure} figures/03_a2_hourly_profiles.png
:alt: Share of noise calls, assault cases, and collisions in each hour of the day, 2021 to 2025.
Share of events in each hour of the day, 2021 to 2025. From [the clock notebook](notebooks/03_clock.ipynb).
:::

## Four parts

::::{grid} 1 1 2 2
:class: parts
:::{card} Context
:link: notebooks/02_trends.ipynb
- How have traffic stops and collisions changed over time, and do they move together?
:::
:::{card} Time
:link: notebooks/03_clock.ipynb
- At what times of day and days of the week do noise complaints, assaults, and collisions peak?
- How do the timing patterns of calls for service and police stops differ across types of calls and stops?
- Do traffic stops happen at the same times as collisions, and does this differ between weekdays and weekends?
:::
:::{card} Academic calendar
:link: notebooks/04_calendar.ipynb
- Do noise complaints and assaults near campus follow the academic calendar (semester vs. breaks) more than in the rest of Berkeley?
- Do noise complaints, assaults, and alcohol-related collisions increase during events like home football games, move-in week, Halloween, and finals?
:::
:::{card} Location
:link: notebooks/06_driving_places.ipynb
- Do areas with more reckless-driving complaints also have more collisions and more traffic stops?
- Are noise complaints concentrated in a few blocks, and do the same blocks stay hotspots over time?
:::
::::

## Where to start

- [Main report](main.ipynb): the full story, with the figures and tables from the analysis notebooks.
- Analysis notebooks: one notebook per section, each listing the files it reads and writes.
- Data: where each table comes from, how it was cleaned, and what each column means.
- [Contributions](contributions.ipynb): who did what, and what each of us learned.

The code and data are on [GitHub](https://github.com/UCB-stat159-f26/final-project-team-16).
