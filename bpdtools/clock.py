"""Count events by hour and weekday and compare the hour profiles of two groups."""

from bpdtools.timeparts import add_time_parts


def timed_hours(events, time_column="local_time"):
    """Keep the events that have a time and add their local time parts.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time.

    Returns
    -------
    pandas.DataFrame
        The rows of `events` with a time, with the columns of
        `add_time_parts` added and `hour` and `weekday` as int.

    Raises
    ------
    KeyError
        If `time_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    """
    # Read the parts from the wall clock time; add_time_parts checks the
    # column and its type.
    parts = add_time_parts(events, time_column=time_column)

    # Drop events without a time. add_time_parts gives them a missing hour
    # and is_weekend False, so they would land on the weekday side.
    parts = parts.loc[parts[time_column].notna()].copy()
    parts["hour"] = parts["hour"].astype(int)
    parts["weekday"] = parts["weekday"].astype(int)
    return parts
