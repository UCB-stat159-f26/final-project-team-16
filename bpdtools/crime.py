"""Functions that clean the BPD crime cases data."""

import pandas as pd

from bpdtools.config import (
    HEADQUARTERS_ADDRESS,
    LOCAL_TIME_ZONE,
    PLACEHOLDER_LAT,
    PLACEHOLDER_LON,
)

# Columns that describe the case itself, so all statute rows of one case
# must agree on them.
CASE_COLUMNS = ("Occurred_Datetime", "Incident_Type", "Block_Address", "lat", "lon")

# Columns that clear_placeholder_points reads.
POINT_COLUMNS = ("Block_Address", "lat", "lon")


def local_times_from_epoch(milliseconds):
    """Convert UTC epoch milliseconds to local date and time in Berkeley.

    Parameters
    ----------
    milliseconds : pandas.Series
        Milliseconds since 1970-01-01 00:00 UTC, as numbers or as text.
        Missing values are allowed.

    Returns
    -------
    pandas.Series
        Datetimes without a time zone that show the America/Los_Angeles wall
        clock time, with the index of `milliseconds`. Missing input gives NaT.

    Raises
    ------
    ValueError
        If a value is not a number.
    """
    # Read text such as "1795264500000" as a number; blanks become NaN.
    try:
        numbers = pd.to_numeric(milliseconds)
    except (TypeError, ValueError) as error:
        raise ValueError(
            "Occurred times must be epoch milliseconds. Remove or correct the "
            f"value that is not a number: {error}"
        ) from error
    # Time zone step: read the numbers as UTC instants, then convert with the
    # time zone rules, so that the offset is -07:00 in daylight saving time
    # and -08:00 otherwise. A fixed offset would be wrong for half the year.
    utc_times = pd.to_datetime(numbers, unit="ms", utc=True)
    local_times = utc_times.dt.tz_convert(LOCAL_TIME_ZONE)
    # Drop the time zone and keep the local wall clock time.
    return local_times.dt.tz_localize(None)


def require_columns(table, needed_columns, table_name):
    """Check that a table has every column that a step needs.

    Parameters
    ----------
    table : pandas.DataFrame
        The table to check.
    needed_columns : sequence of str
        Names of the columns that must be in `table`.
    table_name : str
        Short name of the table for the error message, for example "crime".

    Returns
    -------
    None
        The function returns nothing when every column is there.

    Raises
    ------
    KeyError
        If a column of `needed_columns` is not in `table`. The message names every
        missing column.
    """
    # Collect every missing column, so that one message names them all.
    missing_columns = [name for name in needed_columns if name not in table.columns]
    if missing_columns:
        raise KeyError(
            f"The {table_name} table has no column {missing_columns}. Pass a "
            f"table with all of the columns {list(needed_columns)}."
        )


def one_row_per_case(rows):
    """Keep one row per crime case, after checking that its rows agree.

    The source has one row for each statute of a case. The case fields in
    CASE_COLUMNS must be the same on every row of a case.

    Parameters
    ----------
    rows : pandas.DataFrame
        One row per case and statute. Must contain Case_Number and the
        columns in CASE_COLUMNS.

    Returns
    -------
    pandas.DataFrame
        The first row of each case, in the input order, with a new index
        from 0. Has the same columns as `rows`.

    Raises
    ------
    KeyError
        If Case_Number or a column of CASE_COLUMNS is missing.
    ValueError
        If Case_Number is blank in a row, or if the rows of a case disagree on
        a column of CASE_COLUMNS. The message names the first such case.
    """
    # Stop early with a clear message when a needed column is missing.
    require_columns(rows, ["Case_Number", *CASE_COLUMNS], "crime")
    # A row without a case number cannot be counted once per case.
    blank_cases = rows["Case_Number"].isna()
    if blank_cases.any():
        raise ValueError(
            f"Case_Number is blank in {blank_cases.sum()} rows. Remove those "
            "rows before counting cases."
        )
    # Count the distinct values of each case column within each case. A
    # missing value counts as a value, so a missing and a present value
    # disagree too.
    distinct = rows.groupby("Case_Number", sort=False)[list(CASE_COLUMNS)].nunique(
        dropna=False
    )
    disagree = distinct > 1
    if disagree.to_numpy().any():
        # Report the first case in input order and the first bad column.
        case_number = disagree.any(axis=1).idxmax()
        column = disagree.loc[case_number].idxmax()
        values = rows.loc[rows["Case_Number"] == case_number, column].unique()
        raise ValueError(
            f"Case {case_number} has different {column} values across its "
            f"statute rows: {list(values)}. Correct the rows of this case, or "
            "decide which value to keep, before calling one_row_per_case."
        )
    # Deduplication: all rows of a case agree on the case columns, so keeping
    # the first row loses no case information.
    return rows.drop_duplicates("Case_Number", keep="first").reset_index(drop=True)


def lat_lon_numbers(table, table_name):
    """Read the lat and lon columns of a table as numbers.

    Parameters
    ----------
    table : pandas.DataFrame
        Must contain lat and lon, as numbers or as text. Blank cells are
        allowed.
    table_name : str
        Short name of the table for the error messages, for example "crime".

    Returns
    -------
    latitudes : pandas.Series
        lat as numbers, with the index of `table`. A blank cell gives NaN.
    longitudes : pandas.Series
        lon as numbers, with the index of `table`. A blank cell gives NaN.

    Raises
    ------
    KeyError
        If lat or lon is missing.
    ValueError
        If a lat or lon value is not a number.
    """
    # Stop early with a clear message when a point column is missing.
    require_columns(table, ("lat", "lon"), table_name)
    # Read the coordinates as numbers; a blank cell becomes NaN.
    try:
        latitudes = pd.to_numeric(table["lat"])
        longitudes = pd.to_numeric(table["lon"])
    except (TypeError, ValueError) as error:
        raise ValueError(
            f"lat and lon must be numbers or blank in the {table_name} table. "
            f"Correct or remove the value that is not a number: {error}"
        ) from error
    return latitudes, longitudes


def clear_placeholder_points(cases):
    """Remove the headquarters point from cases at another address.

    The layer gives many cases the map point of police headquarters
    (PLACEHOLDER_LAT, PLACEHOLDER_LON), also when the case address is
    elsewhere. For those cases the point is a placeholder, not the place of
    the case. A case whose address is HEADQUARTERS_ADDRESS keeps the point.

    Parameters
    ----------
    cases : pandas.DataFrame
        Must contain Block_Address, lat, and lon. lat and lon can be numbers
        or text. Missing values are allowed in all three columns.

    Returns
    -------
    pandas.DataFrame
        A copy of `cases` in which lat and lon are missing for each case at
        the placeholder point with another or a blank address. All other
        values are unchanged.

    Raises
    ------
    KeyError
        If Block_Address, lat, or lon is missing.
    ValueError
        If a lat or lon value is not a number.
    """
    # Stop early with a clear message when a needed column is missing.
    require_columns(cases, POINT_COLUMNS, "crime")
    # Read the coordinates as numbers; missing values become NaN.
    latitudes, longitudes = lat_lon_numbers(cases, "crime")
    # Exact equality is safe: the layer writes the placeholder with the same
    # digits every time, so the parsed numbers equal the constants.
    at_placeholder = (latitudes == PLACEHOLDER_LAT) & (longitudes == PLACEHOLDER_LON)
    # Compare addresses in upper case with single spaces and no spaces at
    # the ends, because the layer sometimes writes two spaces in a row.
    addresses = cases["Block_Address"].astype("string").str.upper()
    addresses = addresses.str.split().str.join(" ")
    at_headquarters = (addresses == HEADQUARTERS_ADDRESS).fillna(False).astype(bool)
    # Filter: clear the point only at another address. A blank address
    # cannot show that the case was at headquarters, so it is cleared too.
    to_clear = at_placeholder & ~at_headquarters
    cleared = cases.copy()
    cleared.loc[to_clear, ["lat", "lon"]] = None
    return cleared
