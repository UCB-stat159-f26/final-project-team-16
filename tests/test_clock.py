"""Tests for bpdtools.clock."""

import pandas as pd

from bpdtools.clock import hour_weekday_table, timed_hours


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


def test_hour_weekday_table_puts_event_in_its_cell():
    """Check that one Monday 3 a.m. event is counted in row Monday, column 3."""
    # 2024-11-04 is a Monday.
    table = hour_weekday_table(events_at("2024-11-04 03:15:00"))
    assert table.shape == (7, 24)
    assert table.loc["Monday", 3] == 1
    assert int(table.to_numpy().sum()) == 1


def test_hour_weekday_table_counts_the_repeated_hour_twice():
    """Check two 01:30 events on 2024-11-03, the day the clocks fall back."""
    table = hour_weekday_table(
        events_at("2024-11-03 01:30:00", "2024-11-03 01:30:00", None)
    )
    # Both are Sunday 1 a.m.; the event without a time is not counted.
    assert table.loc["Sunday", 1] == 2
    assert int(table.to_numpy().sum()) == 2
