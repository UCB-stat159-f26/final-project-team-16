"""Tests for bpdtools.timeparts."""

import pandas as pd
import pytest

from bpdtools.timeparts import add_time_parts


def test_add_time_parts_reads_the_wall_clock_on_time_change_days():
    """Check hour, weekday, month, and weekend on both 2024 time change days."""
    # 2024-03-10 and 2024-11-03 are Sundays; 2024-11-04 is a Monday.
    events = pd.DataFrame(
        {
            "local_time": pd.to_datetime(
                ["2024-03-10 03:00:00", "2024-11-03 01:30:00", "2024-11-04 23:59:00"]
            )
        }
    )
    parts = add_time_parts(events)
    assert parts["hour"].tolist() == [3, 1, 23]
    assert parts["weekday"].tolist() == [6, 6, 0]
    assert parts["month"].tolist() == [3, 11, 11]
    assert parts["is_weekend"].tolist() == [True, True, False]


def test_add_time_parts_leaves_the_input_unchanged():
    """Check that the function returns a copy and keeps other columns."""
    events = pd.DataFrame(
        {"id": ["a"], "local_time": pd.to_datetime(["2024-07-06 12:00:00"])}
    )
    parts = add_time_parts(events)
    # The input keeps its two columns; the copy has the four new ones too.
    assert list(events.columns) == ["id", "local_time"]
    assert parts.loc[0, "id"] == "a"
    assert bool(parts.loc[0, "is_weekend"]) is True


def test_add_time_parts_uses_another_column_name():
    """Check that time_column selects the column to read."""
    events = pd.DataFrame({"when": pd.to_datetime(["2024-01-01 08:00:00"])})
    assert add_time_parts(events, time_column="when").loc[0, "hour"] == 8


def test_add_time_parts_names_a_missing_column():
    """Check that a missing time column raises a KeyError with its name."""
    events = pd.DataFrame({"date": pd.to_datetime(["2024-01-01"])})
    with pytest.raises(KeyError, match="local_time"):
        add_time_parts(events)


def test_add_time_parts_rejects_utc_times():
    """Check that a tz-aware column raises a TypeError."""
    # A UTC time would give the UTC hour, not the local hour.
    events = pd.DataFrame(
        {"local_time": pd.to_datetime(["2024-01-01 08:00:00"]).tz_localize("UTC")}
    )
    with pytest.raises(TypeError, match="tz-naive"):
        add_time_parts(events)


def test_add_time_parts_rejects_text_times():
    """Check that times stored as text raise a TypeError."""
    events = pd.DataFrame({"local_time": ["2024-01-01 08:00:00"]})
    with pytest.raises(TypeError, match="tz-naive"):
        add_time_parts(events)
