"""Read the shared Calls for Service and crime cases tables for the analyses."""

import pandas as pd

from bpdtools.calls import TIMESTAMP_FORMAT
from bpdtools.config import (
    BATTERY_CALL_TYPES,
    DATE_FORMAT,
    LOCAL_TIME_ZONE,
    NOISE_CALL_TYPES,
    RECKLESS_CALL_TYPES,
)
from bpdtools.crime import lat_lon_numbers, require_columns
from bpdtools.paths import repo_path

# Call groups and their exact Call Type labels. The label tuples in
# bpdtools/config.py do not overlap, so each label is in one group at most.
CALL_GROUPS = {
    "noise": NOISE_CALL_TYPES,
    "battery": BATTERY_CALL_TYPES,
    "reckless": RECKLESS_CALL_TYPES,
}

# Group of every Call Type that is in none of CALL_GROUPS, blanks included.
OTHER_GROUP = "other"

# Committed tables that the loaders read when no path is given.
CALLS_TABLE = ("data", "processed", "calls_2021_2025.csv.gz")
CASES_TABLE = ("data", "processed", "crime_cases_2021_2025.csv.gz")

# Columns that load_calls needs in the Calls for Service table.
CALL_COLUMNS = ("Incident Number", "CreateDatetime", "date", "Call Type")

# Columns that load_cases needs in the crime cases table.
CASE_TABLE_COLUMNS = (
    "Case_Number",
    "Occurred_Datetime",
    "date",
    "Incident_Type",
    "lat",
    "lon",
)

# Text format of Occurred_Datetime: local wall clock time, no UTC offset.
CASE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def read_text_table(path):
    """Read a CSV table with every column as text.

    Parameters
    ----------
    path : str or pathlib.Path
        CSV file, plain or compressed with gzip.

    Returns
    -------
    pandas.DataFrame
        Every column as str. Blank cells are missing values; text such as
        "NA" or "null" stays text.

    Raises
    ------
    FileNotFoundError
        If `path` does not exist.
    """
    # Keep every value as written: only a blank cell counts as missing, so
    # that a label like "NA" is not read as a missing value.
    return pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])


def classify_call_type(call_types):
    """Put each Call Type label into one call group.

    Parameters
    ----------
    call_types : pandas.Series of str
        Call Type labels of Calls for Service, for example
        "CFS 415E - Noise Disturbance". Missing values are allowed.

    Returns
    -------
    pandas.Series of str
        "noise", "battery", "reckless", or "other" for each label, with the
        index of `call_types`. A missing label gives "other".
    """
    # Start with "other" and overwrite the labels of each group. Matching is
    # exact (isin), because a substring match would also catch other call
    # types such as "CFS 415 - Disturbance".
    groups = pd.Series(OTHER_GROUP, index=call_types.index, dtype="object")
    for group, labels in CALL_GROUPS.items():
        groups[call_types.isin(labels)] = group
    return groups


def load_calls(path=None):
    """Read the 2021-2025 Calls for Service table with local times.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        CSV file to read. The default is
        data/processed/calls_2021_2025.csv.gz in the repository.

    Returns
    -------
    pandas.DataFrame
        One row per call with the columns of the file, where `date` is
        datetime64 at local midnight, and two new columns: `local_time`, the
        tz-naive local wall clock time in America/Los_Angeles, and
        `call_group`, the result of `classify_call_type`.

    Raises
    ------
    KeyError
        If a column of CALL_COLUMNS is missing.
    ValueError
        If a CreateDatetime value does not match "YYYY-MM-DD HH:MM:SS+hh:mm",
        or if a date does not match the local date of its CreateDatetime.
    """
    # Read the committed table unless the caller gives another file.
    path = repo_path(*CALLS_TABLE) if path is None else path
    calls = read_text_table(path)
    require_columns(calls, CALL_COLUMNS, "Calls for Service")

    # Time zone step: parse each value with its own UTC offset, convert the
    # moment to Pacific time with the daylight saving time rules, and keep
    # the wall clock time without the zone. No fixed shift is used.
    try:
        moments = pd.to_datetime(
            calls["CreateDatetime"], format=TIMESTAMP_FORMAT, utc=True
        )
    except ValueError as error:
        raise ValueError(
            "A CreateDatetime value does not match 'YYYY-MM-DD HH:MM:SS+hh:mm'. "
            f"Rebuild the table with scripts/prepare_calls.py. Details: {error}"
        ) from error
    calls["local_time"] = moments.dt.tz_convert(LOCAL_TIME_ZONE).dt.tz_localize(None)

    # Check that the stored date is the local date of each call, so that a
    # table built with another time rule cannot pass unnoticed.
    calls["date"] = pd.to_datetime(calls["date"], format=DATE_FORMAT)
    wrong_date = calls["date"] != calls["local_time"].dt.normalize()
    if wrong_date.any():
        examples = calls.loc[wrong_date, "Incident Number"].head(3).tolist()
        raise ValueError(
            f"{int(wrong_date.sum())} calls have a date that is not the local "
            f"date of CreateDatetime, for example {examples}. Rebuild the "
            "table with scripts/prepare_calls.py."
        )

    # Label each call with its group for the noise, battery, and reckless
    # driving analyses.
    calls["call_group"] = classify_call_type(calls["Call Type"])
    return calls


def load_cases(path=None):
    """Read the 2021-2025 crime cases table with local times and map points.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        CSV file to read. The default is
        data/processed/crime_cases_2021_2025.csv.gz in the repository.

    Returns
    -------
    pandas.DataFrame
        One row per case with the columns of the file, where `date` is
        datetime64 at local midnight, `lat` and `lon` are numbers (NaN when
        blank), and `local_time` is the tz-naive local wall clock time of
        Occurred_Datetime.

    Raises
    ------
    KeyError
        If a column of CASE_TABLE_COLUMNS is missing.
    ValueError
        If an Occurred_Datetime value does not match "YYYY-MM-DD HH:MM:SS",
        if a date does not match it, or if a lat or lon value is not a number.
    """
    # Read the committed table unless the caller gives another file.
    path = repo_path(*CASES_TABLE) if path is None else path
    cases = read_text_table(path)
    require_columns(cases, CASE_TABLE_COLUMNS, "crime cases")

    # Time zone step: Occurred_Datetime is already local wall clock time
    # without an offset, so it is parsed as it is, with no shift.
    try:
        cases["local_time"] = pd.to_datetime(
            cases["Occurred_Datetime"], format=CASE_TIME_FORMAT
        )
    except ValueError as error:
        raise ValueError(
            "An Occurred_Datetime value does not match 'YYYY-MM-DD HH:MM:SS'. "
            f"Rebuild the table with scripts/prepare_crime_cases.py. "
            f"Details: {error}"
        ) from error

    # Check that the stored date is the date of Occurred_Datetime.
    cases["date"] = pd.to_datetime(cases["date"], format=DATE_FORMAT)
    wrong_date = cases["date"] != cases["local_time"].dt.normalize()
    if wrong_date.any():
        examples = cases.loc[wrong_date, "Case_Number"].head(3).tolist()
        raise ValueError(
            f"{int(wrong_date.sum())} cases have a date that is not the date "
            f"of Occurred_Datetime, for example {examples}. Rebuild the table "
            "with scripts/prepare_crime_cases.py."
        )

    # Read the map points as numbers; a blank point stays missing.
    cases["lat"], cases["lon"] = lat_lon_numbers(cases, "crime cases")
    return cases
