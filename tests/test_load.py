"""Tests for bpdtools.load."""

import pandas as pd
import pytest

from bpdtools.load import (
    classify_call_type,
    load_calls,
    load_cases,
    read_text_table,
)

# Header of a small Calls for Service table in the committed format.
CALL_HEADER = "Incident Number,CreateDatetime,date,Call Type\n"

# Header of a small crime cases table in the committed format.
CASE_HEADER = "Case_Number,Occurred_Datetime,date,Incident_Type,lat,lon\n"


def write_table(folder, name, text):
    """Write a small CSV file for a test and give its path.

    Parameters
    ----------
    folder : pathlib.Path
        Folder for the file, for example the tmp_path fixture.
    name : str
        File name.
    text : str
        Full content of the file, header line included.

    Returns
    -------
    pathlib.Path
        Path of the new file.
    """
    # Write with LF line ends, the format of the committed tables.
    path = folder / name
    path.write_text(text, encoding="utf-8", newline="\n")
    return path


def test_read_text_table_keeps_na_text_and_blanks_missing(tmp_path):
    """Check that "NA" stays text and only a blank cell is missing."""
    path = write_table(tmp_path, "t.csv", "a,b\nNA,\n007,x\n")
    table = read_text_table(path)
    # "NA" and the leading zeros stay as written; the blank cell is missing.
    assert table["a"].tolist() == ["NA", "007"]
    assert pd.isna(table.loc[0, "b"])


def test_classify_call_type_puts_each_label_in_its_group():
    """Check one label of each group, an other label, and a missing label."""
    labels = pd.Series(
        [
            "CFS 415E - Noise Disturbance",
            "CFS 242 - Battery",
            "CFS 23103 - Reckless Vehicle",
            "CFS BMCVIO - BMC Violation",
            None,
        ]
    )
    groups = classify_call_type(labels)
    assert groups.tolist() == ["noise", "battery", "reckless", "other", "other"]


def test_classify_call_type_does_not_match_part_of_a_label():
    """Check that a label that only contains a group label stays other."""
    # "CFS 415 - Disturbance" shares "415" with the noise label but is a
    # different call type.
    labels = pd.Series(["CFS 415 - Disturbance", "cfs 415e - noise disturbance"])
    assert classify_call_type(labels).tolist() == ["other", "other"]


def test_load_calls_uses_each_offset_around_both_time_changes(tmp_path):
    """Check local times on the days when daylight saving time starts and ends."""
    # 2024-03-10: 01:59 PST is followed by 03:00 PDT. 2024-11-03: 01:30
    # happens twice, first in PDT (-07:00), then in PST (-08:00).
    text = CALL_HEADER + (
        "c1,2024-03-10 01:59:00-08:00,2024-03-10,CFS 415E - Noise Disturbance\n"
        "c2,2024-03-10 03:00:00-07:00,2024-03-10,CFS 242 - Battery\n"
        "c3,2024-11-03 01:30:00-07:00,2024-11-03,CFS 415E - Noise Disturbance\n"
        "c4,2024-11-03 01:30:00-08:00,2024-11-03,CFS BMCVIO - BMC Violation\n"
    )
    calls = load_calls(write_table(tmp_path, "calls.csv", text))
    expected = pd.to_datetime(
        [
            "2024-03-10 01:59:00",
            "2024-03-10 03:00:00",
            "2024-11-03 01:30:00",
            "2024-11-03 01:30:00",
        ]
    )
    # The wall clock time is kept as written, without a zone and without a
    # fixed shift, and the group comes from the Call Type.
    assert calls["local_time"].tolist() == expected.tolist()
    assert calls["call_group"].tolist() == ["noise", "battery", "noise", "other"]


def test_load_calls_rejects_a_date_that_is_not_the_local_date(tmp_path):
    """Check that a UTC date in the date column raises a ValueError."""
    # 23:30 PDT on July 4 is July 5 in UTC; the stored date must be July 4.
    text = CALL_HEADER + "c1,2024-07-04 23:30:00-07:00,2024-07-05,CFS 242 - Battery\n"
    with pytest.raises(ValueError, match="not the local date"):
        load_calls(write_table(tmp_path, "calls.csv", text))


def test_load_calls_rejects_a_time_without_offset(tmp_path):
    """Check that a CreateDatetime value without its offset raises a ValueError."""
    text = CALL_HEADER + "c1,2024-07-04 23:30:00,2024-07-04,CFS 242 - Battery\n"
    with pytest.raises(ValueError, match="does not match"):
        load_calls(write_table(tmp_path, "calls.csv", text))


def test_load_calls_names_a_missing_column(tmp_path):
    """Check that a table without Call Type raises a KeyError that names it."""
    text = (
        "Incident Number,CreateDatetime,date\nc1,2024-07-04 23:30:00-07:00,2024-07-04\n"
    )
    with pytest.raises(KeyError, match="Call Type"):
        load_calls(write_table(tmp_path, "calls.csv", text))


def test_load_cases_keeps_wall_clock_time_and_reads_points(tmp_path):
    """Check local times without a shift, and numeric points with a blank."""
    # The second case has no map point.
    text = CASE_HEADER + (
        "k1,2024-11-03 01:30:00,2024-11-03,Assault/Battery Felony,37.87,-122.27\n"
        "k2,2024-03-10 03:15:00,2024-03-10,Vandalism,,\n"
    )
    cases = load_cases(write_table(tmp_path, "cases.csv", text))
    assert (
        cases["local_time"].tolist()
        == pd.to_datetime(["2024-11-03 01:30:00", "2024-03-10 03:15:00"]).tolist()
    )
    assert cases.loc[0, "lat"] == 37.87
    assert pd.isna(cases.loc[1, "lon"])


def test_load_cases_rejects_a_date_that_does_not_match(tmp_path):
    """Check that a date other than the date of Occurred_Datetime raises."""
    text = CASE_HEADER + "k1,2024-11-03 01:30:00,2024-11-04,Vandalism,,\n"
    with pytest.raises(ValueError, match="not the date"):
        load_cases(write_table(tmp_path, "cases.csv", text))


def test_load_cases_rejects_a_point_that_is_not_a_number(tmp_path):
    """Check that a lat value that is a word raises a ValueError."""
    text = CASE_HEADER + "k1,2024-11-03 01:30:00,2024-11-03,Vandalism,north,-122.27\n"
    with pytest.raises(ValueError, match="numbers or blank"):
        load_cases(write_table(tmp_path, "cases.csv", text))
