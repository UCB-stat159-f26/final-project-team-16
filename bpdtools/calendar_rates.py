"""Compare semester and winter-break event rates on verified reporting days."""

import pandas as pd


def period_rates(events, calendar, covered_days, near_sectors):
    """Summarize one outcome and campus definition.

    events is a DataFrame of unique events indexed by nonmissing event ID, with
    local date and Sector columns. calendar contains date, semester and
    winter_break flags. covered_days is an iterable of verified local dates
    for this outcome, including days with zero events. near_sectors contains
    numeric beat IDs. Missing sectors denote unassigned or outside points.

    Return a four-row DataFrame indexed by area and period, and a period-level
    audit of excluded events. Rate ratios are missing for undefined comparisons.
    """
    if not events.index.is_unique or events.index.hasnans:
        raise ValueError("Supply one row per event with a unique, nonmissing ID.")
    dates = pd.to_datetime(calendar["date"]).dt.normalize()
    flags = calendar.set_index(dates)[["semester", "winter_break"]]
    if not flags.index.is_unique or not flags.isin([0, 1]).all().all() or (flags.sum(axis=1) > 1).any():
        raise ValueError("Calendar needs unique days and mutually exclusive binary period flags.")
    covered = pd.DatetimeIndex(pd.to_datetime(list(covered_days))).normalize()
    flags = flags.loc[flags.index.isin(covered) & flags.any(axis=1)]
    periods = flags.idxmax(axis=1)
    days = periods.value_counts()

    # Only covered dates contribute to either numerator or denominator.
    period = pd.to_datetime(events["date"]).dt.normalize().map(periods)
    sector = pd.to_numeric(events["Sector"], errors="raise")
    area = sector.isin(list(map(int, near_sectors))).map({True: "near", False: "other"})
    area = area.where(sector.notna())
    order = ["semester", "winter_break"]
    grid = pd.MultiIndex.from_product([["near", "other"], order], names=["area", "period"])
    totals = events.groupby([area, period]).size().reindex(grid, fill_value=0)
    table = totals.to_frame("events")
    table["covered_days"] = table.index.get_level_values("period").map(days).fillna(0).astype(int)
    table["daily_rate"] = table.events.div(table.covered_days.where(table.covered_days.gt(0)))
    rates = table.daily_rate.unstack()
    ratios = rates.semester.div(rates.winter_break.where(rates.winter_break.gt(0)))
    table["semester_to_break_ratio"] = table.index.get_level_values("area").map(ratios)
    audit = pd.DataFrame({"total": period.value_counts(),
                          "unassigned": period[area.isna()].value_counts()}).reindex(order).fillna(0).astype(int)
    audit["unassigned_share"] = audit.unassigned.div(audit.total.where(audit.total.gt(0)))
    return table, audit
