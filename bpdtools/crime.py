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
