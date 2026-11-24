"""Compare semester and winter-break event rates on verified reporting days."""

import pandas as pd


def period_rates(events, calendar, covered_days, near_sectors):
    """Summarize one outcome and campus definition.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event, indexed by unique event ID, with a local date
        and a numeric Sector. A missing sector means the event is unassigned.
    calendar : pandas.DataFrame
        One row per local date with binary semester and winter_break flags.
    covered_days : iterable of date-like
        Reporting dates from the full source, including days with zero
        events of the selected type.
    near_sectors : iterable of int
        Police sectors classified as near campus.

    Returns
    -------
    table : pandas.DataFrame
        Counts, covered days, daily rates and semester-to-break ratios
        indexed by area and period. Undefined rates and ratios are missing.
    audit : pandas.DataFrame
        Total and unassigned events and unassigned share for each period.

    Raises
    ------
    ValueError
        If event IDs are missing or repeated, calendar dates repeat, period
        flags are invalid or overlap, or dates or sectors cannot be parsed.
    """
    if not events.index.is_unique or events.index.hasnans:
        raise ValueError("Supply one row per event with a unique, nonmissing ID.")
    dates = pd.to_datetime(calendar["date"]).dt.normalize()
    flags = calendar.set_index(dates)[["semester", "winter_break"]]
    if not flags.index.is_unique or not flags.isin([0, 1]).all().all() or (flags.sum(axis=1) > 1).any():
        raise ValueError("Calendar needs unique days and mutually exclusive binary period flags.")
    # Intersect source reporting days with the two calendar periods.
    covered = pd.DatetimeIndex(pd.to_datetime(list(covered_days))).normalize()
    flags = flags.loc[flags.index.isin(covered) & flags.any(axis=1)]
    day_period = flags.idxmax(axis=1)
    days = day_period.value_counts()

    # Only covered dates contribute to either numerator or denominator.
    event_period = pd.to_datetime(events["date"]).dt.normalize().map(day_period)
    sector = pd.to_numeric(events["Sector"], errors="raise")
    # Keep missing sectors out of both geographic groups for the audit below.
    area = sector.isin(list(map(int, near_sectors))).map({True: "near", False: "other"})
    area = area.where(sector.notna())
    order = ["semester", "winter_break"]
    grid = pd.MultiIndex.from_product([["near", "other"], order], names=["area", "period"])
    totals = events.groupby([area, event_period]).size().reindex(grid, fill_value=0)
    table = totals.to_frame("events")
    table["covered_days"] = table.index.get_level_values("period").map(days).fillna(0).astype(int)
    # Mask zero denominators while retaining genuine zero-event days.
    table["daily_rate"] = table.events.div(table.covered_days.where(table.covered_days.gt(0)))
    rates = table.daily_rate.unstack()
    ratios = rates.semester.div(rates.winter_break.where(rates.winter_break.gt(0)))
    table["semester_to_break_ratio"] = table.index.get_level_values("area").map(ratios)
    # Count unassigned events within each covered period before spatial exclusion.
    audit = pd.DataFrame({"total": event_period.value_counts(),
                          "unassigned": event_period[area.isna()].value_counts()}).reindex(order).fillna(0).astype(int)
    audit["unassigned_share"] = audit.unassigned.div(audit.total.where(audit.total.gt(0)))
    audit.index.name = "period"
    return table, audit
