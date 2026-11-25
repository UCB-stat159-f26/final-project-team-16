"""Tests for bpdtools.trends."""

import pandas as pd
import pytest

from bpdtools.trends import monthly_counts


def small_events():
    """Build four rows: two in January 2024, one in March, one with no time.

    Returns
    -------
    pandas.DataFrame
        Columns `when` (tz-naive datetime64) and `event_id` (text). The
        first two rows share the id "a".
    """
    return pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-03-02", None]),
            "event_id": ["a", "a", "b", "c"],
        }
    )


def test_monthly_counts_fills_empty_months_and_skips_empty_times():
    """Check counts by row: February gets 0 and the empty time is left out."""
    counts = monthly_counts(small_events(), "when")
    assert counts.index.astype(str).tolist() == ["2024-01", "2024-02", "2024-03"]
    assert counts.tolist() == [2, 0, 1]
    assert counts.dtype == "int64"


def test_monthly_counts_counts_a_repeated_id_once():
    """Check counts by id: the two January rows of id "a" count once."""
    counts = monthly_counts(small_events(), "when", id_column="event_id")
    assert counts.index.astype(str).tolist() == ["2024-01", "2024-02", "2024-03"]
    assert counts.tolist() == [1, 0, 1]


def test_monthly_counts_puts_a_repeated_id_in_its_earliest_month():
    """Check that an id with rows in two months counts in the earlier month."""
    # The February row comes first in the table, so the row order must not
    # decide the month.
    events = pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-02-10", "2024-01-15", "2024-02-20"]),
            "event_id": ["a", "a", "b"],
        }
    )
    counts = monthly_counts(events, "when", id_column="event_id")
    assert counts.index.astype(str).tolist() == ["2024-01", "2024-02"]
    assert counts.tolist() == [1, 1]


def test_monthly_counts_counts_each_row_with_a_missing_id():
    """Check that two rows without an id are two events, not one."""
    events = pd.DataFrame(
        {
            "when": pd.to_datetime(["2024-01-05", "2024-01-06", "2024-01-07"]),
            "event_id": ["a", None, None],
        }
    )
    counts = monthly_counts(events, "when", id_column="event_id")
    assert counts.tolist() == [3]


def test_monthly_counts_names_a_missing_time_column():
    """Check that a missing time column raises a KeyError with its name."""
    with pytest.raises(KeyError, match="missing"):
        monthly_counts(small_events(), time_column="missing")


def test_monthly_counts_names_a_missing_id_column():
    """Check that a missing id column raises a KeyError with its name."""
    with pytest.raises(KeyError, match="no_such_id"):
        monthly_counts(small_events(), "when", id_column="no_such_id")


def test_monthly_counts_rejects_text_times():
    """Check that times stored as text raise a TypeError."""
    events = pd.DataFrame({"when": ["2024-01-05"]})
    with pytest.raises(TypeError, match="tz-naive"):
        monthly_counts(events, "when")


def test_monthly_counts_names_the_index_and_the_series():
    """Check the names "month" and "count" and the monthly PeriodIndex."""
    counts = monthly_counts(small_events(), "when")
    assert counts.name == "count"
    assert counts.index.name == "month"
    assert isinstance(counts.index, pd.PeriodIndex)
    assert counts.index.freqstr == "M"


def test_monthly_counts_leaves_the_input_unchanged():
    """Check that the table is the same before and after the call."""
    events = small_events()
    before = events.copy(deep=True)
    monthly_counts(events, "when", id_column="event_id")
    pd.testing.assert_frame_equal(events, before)


def test_monthly_counts_returns_an_empty_series_for_an_empty_table():
    """Check that a table with no rows gives an empty Series named "count"."""
    events = pd.DataFrame({"when": pd.to_datetime([])})
    counts = monthly_counts(events, "when")
    assert counts.empty
    assert counts.name == "count"
    assert counts.index.name == "month"
