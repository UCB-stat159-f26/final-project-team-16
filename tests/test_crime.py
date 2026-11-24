"""Tests for bpdtools.crime."""

from datetime import datetime, timezone

import pandas as pd
import pytest

from bpdtools.crime import local_times_from_epoch, one_row_per_case, require_columns


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


def test_require_columns_accepts_a_table_with_every_column():
    """Check that a table with all needed columns raises nothing."""
    # An extra column, Case_Number, is allowed.
    table = pd.DataFrame(
        {"Case_Number": ["2024-1"], "lat": ["37.87"], "lon": ["-122.27"]}
    )
    assert require_columns(table, ["lat", "lon"], "crime") is None


def test_require_columns_names_every_missing_column():
    """Check that the KeyError names the table and each missing column."""
    # Both point columns are absent.
    table = pd.DataFrame({"Case_Number": ["2024-1"]})
    with pytest.raises(KeyError, match=r"crime table has no column \['lat', 'lon'\]"):
        require_columns(table, ["Case_Number", "lat", "lon"], "crime")


def make_case_rows(incident_types):
    """Build a small crime table with one case and one row per statute.

    Parameters
    ----------
    incident_types : list of str
        Incident_Type of each statute row, in order.

    Returns
    -------
    pandas.DataFrame
        Rows of case 2024-00000001 with the columns that one_row_per_case
        checks, plus a Statute column that differs between rows.
    """
    # Repeat the same case fields on every statute row, as in the source.
    n_statutes = len(incident_types)
    return pd.DataFrame(
        {
            "Case_Number": ["2024-00000001"] * n_statutes,
            "Occurred_Datetime": ["2024-12-25 22:25:00"] * n_statutes,
            "Incident_Type": incident_types,
            "Statute": [f"PC {number}" for number in range(n_statutes)],
            "Block_Address": ["2400 TELEGRAPH AVE"] * n_statutes,
            "lat": ["37.8676"] * n_statutes,
            "lon": ["-122.2590"] * n_statutes,
        }
    )


def test_one_row_per_case_collapses_two_statutes():
    """Check that a case with two statute rows and a second case give 2 rows."""
    # One case with two statute rows that agree on the case fields.
    case_rows = make_case_rows(["Assault/Battery Felony"] * 2)
    # A second case with one row and a missing point, which must stay.
    other_case = case_rows.iloc[[0]].assign(
        Case_Number="2024-00000002", lat=None, lon=None
    )
    result = one_row_per_case(pd.concat([case_rows, other_case]))
    assert list(result["Case_Number"]) == ["2024-00000001", "2024-00000002"]
    # The first statute row of the case is the one that is kept.
    assert result.loc[0, "Statute"] == "PC 0"


def test_one_row_per_case_rejects_two_incident_types():
    """Check that two Incident_Type values in one case raise a ValueError."""
    # One case whose two statute rows have different Incident_Type values.
    case_rows = make_case_rows(
        ["Assault/Battery Felony", "Assault/Battery Misdemeanor"]
    )
    # The error must name the case and the column that disagree.
    with pytest.raises(ValueError, match="2024-00000001 has different Incident_Type"):
        one_row_per_case(case_rows)
