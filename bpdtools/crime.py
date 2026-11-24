"""Functions that clean the BPD crime cases data."""

import pandas as pd

from bpdtools.config import LOCAL_TIME_ZONE


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
