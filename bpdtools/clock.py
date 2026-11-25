"""Count events by hour and weekday and compare the hour profiles of two groups."""

import pandas as pd

from bpdtools.timeparts import add_time_parts

# Hours of the day and day numbers of the week (Monday is 0) in each table.
HOURS = range(24)
WEEKDAYS = range(7)

# Names of the weekdays in the order of their day numbers.
WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)


def timed_hours(events, time_column="local_time"):
    """Keep the events that have a time and add their local time parts.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time.

    Returns
    -------
    pandas.DataFrame
        The rows of `events` with a time, with the columns of
        `add_time_parts` added and `hour` and `weekday` as int.

    Raises
    ------
    KeyError
        If `time_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    """
    # Read the parts from the wall clock time; add_time_parts checks the
    # column and its type.
    parts = add_time_parts(events, time_column=time_column)

    # Drop events without a time. add_time_parts gives them a missing hour
    # and is_weekend False, so they would land on the weekday side.
    parts = parts.loc[parts[time_column].notna()].copy()
    parts["hour"] = parts["hour"].astype(int)
    parts["weekday"] = parts["weekday"].astype(int)
    return parts


def hour_weekday_table(events, time_column="local_time"):
    """Count events by day of the week and hour of the day.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time, such
        as the `local_time` column of the loaders.

    Returns
    -------
    pandas.DataFrame
        A table with 7 rows (Monday to Sunday) and 24 columns (hours 0 to
        23). Each cell is the number of events. Events without a time are
        not counted.

    Raises
    ------
    KeyError
        If `time_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    """
    parts = timed_hours(events, time_column=time_column)

    # Count each weekday and hour pair, and keep empty cells as zeros so
    # that the table is always 7 by 24.
    table = (
        pd.crosstab(parts["weekday"], parts["hour"])
        .reindex(index=WEEKDAYS, columns=HOURS, fill_value=0)
        .astype(int)
    )
    table.index = pd.Index(WEEKDAY_NAMES, name="weekday")
    table.columns.name = "hour"
    return table


def hourly_profile(events, time_column="local_time", group_column=None):
    """Compute the share of events in each hour of the day.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`, and `group_column`
        when one is given.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time.
    group_column : str, optional
        Column that splits the events into groups, such as `call_group`.
        Without it, all events form one group named "all".

    Returns
    -------
    pandas.DataFrame
        24 rows (hours 0 to 23) and one column per group. Each column holds
        the share of the group's timed events in each hour and sums to 1.

    Raises
    ------
    KeyError
        If `time_column` or `group_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    ValueError
        If no event has a time.
    """
    # Check the group column before the time column, so that the error
    # names the column that is missing.
    if group_column is not None and group_column not in events.columns:
        raise KeyError(f"events has no column {group_column!r}.")
    parts = timed_hours(events, time_column=time_column)
    if parts.empty:
        raise ValueError("No event has a time, so there is no hour profile.")

    # Count each hour per group, then divide by the group total. Without a
    # group column, every event gets the group "all".
    if group_column is None:
        groups = pd.Series("all", index=parts.index)
    else:
        groups = parts[group_column]
    counts = (
        pd.crosstab(parts["hour"], groups)
        .reindex(index=HOURS, fill_value=0)
        .rename_axis(index="hour", columns=group_column)
    )
    return counts / counts.sum()
