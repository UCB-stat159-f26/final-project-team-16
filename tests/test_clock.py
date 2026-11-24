"""Tests for bpdtools.clock."""

import pandas as pd

from bpdtools.clock import timed_hours


def events_at(*times):
    """Make an events table with one local_time per argument.

    Parameters
    ----------
    *times : str or None
        Local wall clock times such as "2024-11-04 03:15:00"; None gives a
        missing time.

    Returns
    -------
    pandas.DataFrame
        One row per time, with a tz-naive datetime64 `local_time` column.
    """
    return pd.DataFrame({"local_time": pd.to_datetime(list(times))})


def test_timed_hours_drops_missing_times_and_keeps_int_hours():
    """Check that an event without a time is dropped, not put on a weekday."""
    parts = timed_hours(events_at("2024-11-02 22:10:00", None))
    assert len(parts) == 1
    assert parts["hour"].tolist() == [22]
    assert parts["hour"].dtype.kind == "i"
    assert bool(parts["is_weekend"].iloc[0]) is True
