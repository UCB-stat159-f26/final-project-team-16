"""Tests for bpdtools.clock."""

import numpy as np
import pandas as pd
import pytest

from bpdtools.clock import (
    hour_weekday_table,
    hourly_profile,
    profile_overlap,
    timed_hours,
)


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


def test_hourly_profile_gives_shares_per_group():
    """Check that each group column holds shares that sum to 1."""
    events = events_at(
        "2024-01-01 08:00:00", "2024-01-01 08:30:00", "2024-01-01 20:00:00"
    )
    events["call_group"] = ["noise", "noise", "battery"]
    profile = hourly_profile(events, group_column="call_group")
    assert profile.shape == (24, 2)
    assert profile.loc[8, "noise"] == 1.0
    assert profile.loc[20, "battery"] == 1.0
    assert np.allclose(profile.sum(), 1.0)


def test_hourly_profile_without_groups_uses_one_column():
    """Check the single "all" column when no group column is given."""
    profile = hourly_profile(events_at("2024-01-01 08:00:00", "2024-01-01 09:00:00"))
    assert list(profile.columns) == ["all"]
    assert profile.loc[8, "all"] == 0.5


def test_hourly_profile_rejects_events_without_times():
    """Check that a table with no timed event raises a ValueError."""
    with pytest.raises(ValueError, match="No event has a time"):
        hourly_profile(events_at(None))


def test_hourly_profile_names_a_missing_group_column():
    """Check that a missing group column raises a KeyError with its name."""
    with pytest.raises(KeyError, match="call_group"):
        hourly_profile(events_at("2024-01-01 08:00:00"), group_column="call_group")


def test_profile_overlap_of_same_disjoint_and_half_shared_profiles():
    """Check the overlap values 1, 0, and 0.5."""
    at_eight = np.zeros(24)
    at_eight[8] = 1.0
    at_nine = np.zeros(24)
    at_nine[9] = 1.0
    eight_and_nine = (at_eight + at_nine) / 2
    assert profile_overlap(at_eight, at_eight) == 1.0
    assert profile_overlap(at_eight, at_nine) == 0.0
    assert profile_overlap(at_eight, eight_and_nine) == 0.5


def test_profile_overlap_rejects_counts_and_short_profiles():
    """Check that counts or a profile without 24 hours raise a ValueError."""
    counts = np.ones(24)
    with pytest.raises(ValueError, match="sum to 1"):
        profile_overlap(counts, counts / 24)
    with pytest.raises(ValueError, match="24 values"):
        profile_overlap(np.ones(23) / 23, np.ones(24) / 24)
