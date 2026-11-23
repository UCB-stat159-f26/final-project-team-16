"""Turn Calls for Service timestamps into local dates and list covered days."""

import pandas as pd

from bpdtools.config import LOCAL_TIME_ZONE

# Pattern of a UTC offset at the end of a timestamp, for example "-07:00".
OFFSET_PATTERN = r"[+-]\d{2}:\d{2}$"

# Exact text format of CreateDatetime, for example "2024-11-03 01:30:00-07:00".
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S%z"

# How many wrong values to show as examples in an error message.
N_EXAMPLES = 3


def local_dates(timestamps):
    """Find the local calendar date of each timestamp with a UTC offset.

    Parameters
    ----------
    timestamps : pandas.Series of str
        Timestamps such as "2024-11-03 01:30:00-07:00". Each one must end in
        its UTC offset. Blank strings and missing values are allowed.

    Returns
    -------
    pandas.Series
        Tz-naive datetime64 values at midnight of the local date in the
        America/Los_Angeles time zone, with the same index as `timestamps`.
        Blank or missing timestamps give NaT.

    Raises
    ------
    ValueError
        If a non-blank timestamp has no UTC offset or does not match the
        format "YYYY-MM-DD HH:MM:SS+hh:mm".
    """
    # Treat missing values and whitespace-only strings as blank.
    text = timestamps.astype("string").str.strip()
    is_blank = text.isna() | (text == "")

    # Refuse values without an offset before parsing, so that the error
    # gives their count and a few examples. Without an offset the local
    # date of a value is unknown.
    has_offset = text.str.contains(OFFSET_PATTERN, regex=True)
    no_offset = ~is_blank & ~has_offset.fillna(False).astype(bool)
    if no_offset.any():
        examples = text[no_offset].head(N_EXAMPLES).tolist()
        raise ValueError(
            f"{int(no_offset.sum())} timestamps have no UTC offset, for "
            f"example {examples}. Give each value its offset, such as "
            "'2024-11-03 01:30:00-07:00'."
        )

    # Parse each value with its own offset, so the result is the exact
    # moment in UTC; no fixed shift is used. Blank values become NaT.
    try:
        moments = pd.to_datetime(text.mask(is_blank), format=TIMESTAMP_FORMAT, utc=True)
    except ValueError as error:
        raise ValueError(
            "A timestamp does not match the format 'YYYY-MM-DD HH:MM:SS+hh:mm'. "
            f"Correct the value or remove the row. Details: {error}"
        ) from error

    # Time zone step: convert each moment to Pacific time with the daylight
    # saving time rules, drop the zone, and keep only the date.
    return moments.dt.tz_convert(LOCAL_TIME_ZONE).dt.tz_localize(None).dt.normalize()


def covered_days(dates):
    """List the local dates on which a table has at least one record.

    Pass the dates of the FULL, unfiltered table (all call types), not a
    series that was filtered to one event type. A day with records but no
    event of one type is still a covered day: its count for that type is a
    real zero, not a gap in the data. A filtered series would drop such days
    and make daily rates too high.

    Parameters
    ----------
    dates : pandas.Series of datetime64
        Tz-naive local dates of every record of the unfiltered table, for
        example the result of `local_dates`. NaT values are ignored.

    Returns
    -------
    pandas.DatetimeIndex
        The sorted unique local dates (at midnight) with at least one record.

    Raises
    ------
    TypeError
        If `dates` does not hold tz-naive datetime64 values.
    """
    # Accept only tz-naive dates, so that text or UTC values cannot slip in.
    if not pd.api.types.is_datetime64_dtype(dates):
        raise TypeError(
            f"dates has dtype {dates.dtype}; it must be tz-naive datetime64. "
            "Use local_dates(), or read the table with parse_dates=['date']."
        )
    # Drop undated records, reduce each value to its day, and keep each day
    # once (this is a deduplication of days, not of records).
    days = dates.dropna().dt.normalize().unique()
    return pd.DatetimeIndex(days).sort_values()
