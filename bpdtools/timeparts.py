"""Derive the local hour, weekday, month, and weekend flag of events."""

import pandas as pd

# Day numbers of Saturday and Sunday in pandas, where Monday is 0.
WEEKEND_DAYS = (5, 6)


def add_time_parts(events, time_column="local_time"):
    """Add the local hour, weekday, month, and a weekend flag to each event.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column that holds local wall clock
        times in America/Los_Angeles, such as the `local_time` column of
        `load_calls` and `load_cases`.

    Returns
    -------
    pandas.DataFrame
        A copy of `events` with four new columns: `hour` (0 to 23),
        `weekday` (0 for Monday to 6 for Sunday), `month` (1 to 12), and
        `is_weekend` (True on Saturday and Sunday). A missing time gives
        missing parts and `is_weekend` False.

    Raises
    ------
    KeyError
        If `time_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    """
    # Stop with a clear message when the time column is missing.
    if time_column not in events.columns:
        raise KeyError(
            f"events has no column {time_column!r}. Pass the name of its "
            "local time column, for example time_column='local_time'."
        )

    # Accept only tz-naive local wall clock times. A tz-aware or UTC column
    # would give the hour in another time zone.
    times = events[time_column]
    if not pd.api.types.is_datetime64_dtype(times):
        raise TypeError(
            f"{time_column!r} has dtype {times.dtype}; it must be tz-naive "
            "datetime64 in local time. Convert UTC times with "
            ".dt.tz_convert('America/Los_Angeles').dt.tz_localize(None)."
        )

    # Read each part from the wall clock time, so that the hour stays right
    # on the days when daylight saving time starts and ends.
    result = events.copy()
    result["hour"] = times.dt.hour
    result["weekday"] = times.dt.day_of_week
    result["month"] = times.dt.month
    result["is_weekend"] = result["weekday"].isin(WEEKEND_DAYS)
    return result
