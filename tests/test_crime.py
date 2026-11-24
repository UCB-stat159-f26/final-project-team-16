"""Tests for bpdtools.crime."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from bpdtools.crime import local_times_from_epoch


def utc_milliseconds(year, month, day, hour, minute):
    """Give the epoch milliseconds of a UTC date and time.

    Parameters
    ----------
    year, month, day, hour, minute : int
        The date and time in UTC.

    Returns
    -------
    int
        Milliseconds since 1970-01-01 00:00 UTC.
    """
    # Build the instant in UTC with the standard library, not with the
    # function under test, so that the expected values are independent.
    instant = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    return int(instant.timestamp()) * 1000


def test_local_times_use_daylight_saving_time_in_july():
    """Check that 2024-07-04 19:00 UTC is 12:00 local time (UTC-7)."""
    # July: 19:00 UTC minus 7 hours is 12:00 local time.
    epoch = pd.Series([utc_milliseconds(2024, 7, 4, 19, 0)])
    result = local_times_from_epoch(epoch)
    assert result.iloc[0] == pd.Timestamp("2024-07-04 12:00:00")


def test_local_times_use_standard_time_in_december():
    """Check that 2024-12-02 08:15 UTC is 00:15 local time (UTC-8)."""
    # December: 08:15 UTC minus 8 hours is 00:15 local time.
    epoch = pd.Series([utc_milliseconds(2024, 12, 2, 8, 15)])
    result = local_times_from_epoch(epoch)
    assert result.iloc[0] == pd.Timestamp("2024-12-02 00:15:00")


def test_local_times_keep_the_local_day_when_utc_is_the_next_day():
    """Check that 2024-12-26 06:25 UTC stays on 2024-12-25 at 22:25 local time."""
    # The epoch is given as text, as it appears in the raw CSV.
    epoch = pd.Series([str(utc_milliseconds(2024, 12, 26, 6, 25))])
    result = local_times_from_epoch(epoch)
    assert result.iloc[0] == pd.Timestamp("2024-12-25 22:25:00")


def test_local_times_give_nat_for_a_missing_value():
    """Check that a missing epoch gives NaT and the result has no time zone."""
    # One missing value next to one valid value.
    epoch = pd.Series([None, str(utc_milliseconds(2024, 7, 4, 19, 0))])
    result = local_times_from_epoch(epoch)
    assert pd.isna(result.iloc[0])
    assert result.dt.tz is None


def test_local_times_reject_text_that_is_not_a_number():
    """Check that a value such as "2024-07-04" raises a ValueError."""
    # A date string is not epoch milliseconds.
    with pytest.raises(ValueError, match="epoch milliseconds"):
        local_times_from_epoch(pd.Series(["2024-07-04"]))
