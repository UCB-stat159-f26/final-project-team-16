"""Count events in each calendar month for the trend comparisons."""

import pandas as pd

# Calendar month frequency of the result index.
MONTH_FREQUENCY = "M"

# Names of the result index and of the result Series.
MONTH_INDEX_NAME = "month"
COUNT_NAME = "count"


def monthly_counts(events, time_column, id_column=None):
    """Count events in each calendar month.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event, or several rows per event when `id_column` is
        given. Must contain `time_column`.
    time_column : str
        Name of a tz-naive datetime64 column that holds the local date or
        the local time of each row, such as `StopDate` of `load_stops` or
        `Date` of `load_collisions`.
    id_column : str, optional
        Name of a column that identifies an event. When given, rows that
        share an id count once, in the month of their earliest time. A row
        with a missing id cannot be matched to another row, so it counts
        on its own.

    Returns
    -------
    pandas.Series
        Integer counts named "count", with a monthly PeriodIndex named
        "month". The index holds every month from the first event to the
        last, and a month with no event has the count 0. Rows with a
        missing time are not counted. The result is empty when no row has
        a time.

    Raises
    ------
    KeyError
        If `time_column` or `id_column` is not a column of `events`.
    TypeError
        If `time_column` holds values and is not tz-naive datetime64.
    """
    # Stop with a clear message when a needed column is missing.
    needed_columns = [time_column] if id_column is None else [time_column, id_column]
    for column in needed_columns:
        if column not in events.columns:
            raise KeyError(
                f"events has no column {column!r}. Its columns are "
                f"{list(events.columns)}; pass one of these names."
            )

    # Filter: keep only the rows that have a time. A row without a time
    # cannot be placed in a month. Selecting the rows makes a new table, so
    # the input stays unchanged.
    dated_rows = events.loc[events[time_column].notna(), needed_columns]

    # Return an empty result when no row has a time, so that the caller
    # does not need a special case for an empty table.
    if dated_rows.empty:
        return pd.Series(
            [],
            index=pd.PeriodIndex([], freq=MONTH_FREQUENCY, name=MONTH_INDEX_NAME),
            name=COUNT_NAME,
            dtype="int64",
        )

    # Accept only tz-naive datetime64 values. Text would not have a month,
    # and a tz-aware column could put an event in the month of another
    # time zone.
    event_times = dated_rows[time_column]
    if not pd.api.types.is_datetime64_dtype(event_times):
        raise TypeError(
            f"{time_column!r} has dtype {event_times.dtype}; it must be "
            "tz-naive datetime64 in local time. Parse text with "
            "pandas.to_datetime, or use a column that a bpdtools loader parsed."
        )

    # Deduplication rule: when an id column is given, rows that share an id
    # are one event, and the event belongs to the month of its earliest row.
    if id_column is not None:
        has_id = dated_rows[id_column].notna()
        # Earliest time of each id. groupby leaves out the rows with a
        # missing id, so these rows are added back one by one.
        earliest_by_id = dated_rows[has_id].groupby(id_column)[time_column].min()
        event_times = pd.concat(
            [earliest_by_id, dated_rows.loc[~has_id, time_column]],
            ignore_index=True,
        )

    # Count the events of each month, then add the months without events
    # between the first and the last event with the count 0.
    event_months = event_times.dt.to_period(MONTH_FREQUENCY)
    all_months = pd.period_range(
        event_months.min(),
        event_months.max(),
        freq=MONTH_FREQUENCY,
        name=MONTH_INDEX_NAME,
    )
    counts = event_months.value_counts().reindex(all_months, fill_value=0)

    # Give the result its documented name and integer type.
    return counts.astype("int64").rename(COUNT_NAME)
