"""Tests for bpdtools.calls."""

import pandas as pd
import pytest

from bpdtools.calls import local_dates


def test_local_dates_reads_summer_and_winter_offsets():
    """Check that -07:00 and -08:00 rows keep their local calendar dates."""
    # One summer (PDT) and one winter (PST) value, both local time.
    timestamps = pd.Series(["2024-07-04 12:00:00-07:00", "2024-01-15 08:00:00-08:00"])
    result = local_dates(timestamps)
    expected = pd.to_datetime(pd.Series(["2024-07-04", "2024-01-15"]))
    assert result.tolist() == expected.tolist()


def test_local_dates_converts_a_utc_value_to_the_previous_local_day():
    """Check that 05:00 UTC on July 1 is June 30 in Berkeley (22:00 PDT)."""
    # Time zone step: a value in UTC must be converted, not sliced as text.
    timestamps = pd.Series(["2024-07-01 05:00:00+00:00"])
    assert local_dates(timestamps).iloc[0] == pd.Timestamp("2024-06-30")


def test_local_dates_on_the_spring_daylight_saving_day():
    """Check both sides of the 2024-03-10 change from -08:00 to -07:00."""
    # The last second before the change and the first second after it.
    timestamps = pd.Series(["2024-03-10 01:59:59-08:00", "2024-03-10 03:00:00-07:00"])
    result = local_dates(timestamps)
    assert result.tolist() == [pd.Timestamp("2024-03-10")] * 2


def test_local_dates_on_the_fall_daylight_saving_day():
    """Check that both 01:30 rows of 2024-11-03 (-07:00, -08:00) stay on 11-03."""
    # 01:30 occurs twice on this day: first in PDT, then again in PST.
    timestamps = pd.Series(["2024-11-03 01:30:00-07:00", "2024-11-03 01:30:00-08:00"])
    result = local_dates(timestamps)
    assert result.tolist() == [pd.Timestamp("2024-11-03")] * 2


def test_local_dates_keeps_a_late_evening_row_on_its_day():
    """Check that 23:59 local on New Year's Eve is not moved to January 1."""
    # Both values are already the next day in UTC, so a wrong shift shows.
    timestamps = pd.Series(["2024-12-31 23:59:00-08:00", "2024-08-31 23:59:00-07:00"])
    result = local_dates(timestamps)
    expected = [pd.Timestamp("2024-12-31"), pd.Timestamp("2024-08-31")]
    assert result.tolist() == expected


def test_local_dates_gives_nat_for_blank_values_and_keeps_the_index():
    """Check that blank and missing values give NaT, with the index kept."""
    # An empty string and a None next to one dated value, with a text index.
    timestamps = pd.Series(
        ["2024-05-01 10:00:00-07:00", "", None], index=["a", "b", "c"]
    )
    result = local_dates(timestamps)
    assert pd.api.types.is_datetime64_dtype(result)
    assert result.index.tolist() == ["a", "b", "c"]
    assert result["a"] == pd.Timestamp("2024-05-01")
    assert result[["b", "c"]].isna().all()


def test_local_dates_rejects_a_value_without_offset():
    """Check that a timestamp without a UTC offset raises a ValueError."""
    # The second value has no offset, so its local date is unknown.
    timestamps = pd.Series(["2024-05-01 10:00:00-07:00", "2024-05-01 10:00:00"])
    with pytest.raises(ValueError, match="no UTC offset"):
        local_dates(timestamps)
