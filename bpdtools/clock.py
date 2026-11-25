"""Count events by hour and weekday and compare the hour profiles of two groups."""

import numpy as np
import pandas as pd

from bpdtools.config import SEED
from bpdtools.timeparts import add_time_parts

# Hours of the day and day numbers of the week (Monday is 0) in each table.
HOURS = range(24)
WEEKDAYS = range(7)

# Names of the weekdays in the order of their day numbers.
WEEKDAY_NAMES = (
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
)

# Number of label shuffles in overlap_permutation_test.
DEFAULT_PERMUTATIONS = 9999

# Allowed difference from 1 for the sum of the shares of a profile.
SHARE_SUM_TOLERANCE = 1e-9

# Rounding margin when a shuffled overlap is compared with the observed one.
OVERLAP_TOLERANCE = 1e-12


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


def hour_weekday_table(events, time_column="local_time"):
    """Count events by day of the week and hour of the day.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time, such
        as the `local_time` column of the loaders.

    Returns
    -------
    pandas.DataFrame
        A table with 7 rows (Monday to Sunday) and 24 columns (hours 0 to
        23). Each cell is the number of events. Events without a time are
        not counted.

    Raises
    ------
    KeyError
        If `time_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    """
    parts = timed_hours(events, time_column=time_column)

    # Count each weekday and hour pair, and keep empty cells as zeros so
    # that the table is always 7 by 24.
    table = (
        pd.crosstab(parts["weekday"], parts["hour"])
        .reindex(index=WEEKDAYS, columns=HOURS, fill_value=0)
        .astype(int)
    )
    table.index = pd.Index(WEEKDAY_NAMES, name="weekday")
    table.columns.name = "hour"
    return table


def hourly_profile(events, time_column="local_time", group_column=None):
    """Compute the share of events in each hour of the day.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column`, and `group_column`
        when one is given.
    time_column : str, default "local_time"
        Name of a tz-naive datetime64 column in local wall clock time.
    group_column : str, optional
        Column that splits the events into groups, such as `call_group`.
        Without it, all events form one group named "all".

    Returns
    -------
    pandas.DataFrame
        24 rows (hours 0 to 23) and one column per group. Each column holds
        the share of the group's timed events in each hour and sums to 1.

    Raises
    ------
    KeyError
        If `time_column` or `group_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    ValueError
        If no event has a time.
    """
    # Check the group column before the time column, so that the error
    # names the column that is missing.
    if group_column is not None and group_column not in events.columns:
        raise KeyError(f"events has no column {group_column!r}.")
    parts = timed_hours(events, time_column=time_column)
    if parts.empty:
        raise ValueError("No event has a time, so there is no hour profile.")

    # Count each hour per group, then divide by the group total. Without a
    # group column, every event gets the group "all".
    if group_column is None:
        groups = pd.Series("all", index=parts.index)
    else:
        groups = parts[group_column]
    counts = (
        pd.crosstab(parts["hour"], groups)
        .reindex(index=HOURS, fill_value=0)
        .rename_axis(index="hour", columns=group_column)
    )
    return counts / counts.sum()


def profile_overlap(first, second):
    """Measure how much two hour profiles agree.

    The overlap is the sum over the hours of the smaller of the two shares.
    It is 1 when the profiles are the same and 0 when the two groups never
    happen in the same hour.

    Parameters
    ----------
    first, second : pandas.Series or numpy.ndarray of float
        Shares of events in hours 0 to 23. Each has 24 values that are not
        negative and sum to 1, for example a column of `hourly_profile`.

    Returns
    -------
    float
        The overlap, from 0 to 1.

    Raises
    ------
    ValueError
        If a profile does not have 24 values, has a negative value, or does
        not sum to 1.
    """
    shares = []
    for name, profile in (("first", first), ("second", second)):
        values = np.asarray(profile, dtype=float)
        # A profile must be a full day of shares, so that the hours line up.
        if values.shape != (24,):
            raise ValueError(f"{name} has shape {values.shape}; it needs 24 values.")
        if (values < 0).any() or abs(values.sum() - 1) > SHARE_SUM_TOLERANCE:
            raise ValueError(
                f"{name} must hold shares that are not negative and sum to 1; "
                f"its sum is {values.sum():.6f}. Use hourly_profile to build it."
            )
        shares.append(values)
    return float(np.minimum(shares[0], shares[1]).sum())


def overlap_permutation_test(
    first_hours, second_hours, n_permutations=DEFAULT_PERMUTATIONS, seed=SEED
):
    """Test whether two groups of events have different hour profiles.

    The test pools the hours of both groups, shuffles the group labels, and
    recomputes the overlap of the two hour profiles each time. A low
    p-value means that the observed overlap is lower than label shuffles
    give. The test treats events as independent of each other.

    Parameters
    ----------
    first_hours, second_hours : pandas.Series or numpy.ndarray of int
        Local hour (0 to 23) of each event in the two groups, for example
        the `hour` column of `timed_hours`.
    n_permutations : int, default DEFAULT_PERMUTATIONS
        Number of label shuffles.
    seed : int, default SEED
        Seed of the random number generator, so that each run gives the
        same p-value.

    Returns
    -------
    dict
        "overlap": the observed overlap (float), "p_value": the share of
        shuffles, with the observed labels counted as one, whose overlap is
        at most the observed overlap (float), and "n_permutations" (int).

    Raises
    ------
    ValueError
        If a group is empty, if an hour is not an integer from 0 to 23, or
        if `n_permutations` is less than 1.
    """
    groups = []
    for name, hours in (("first_hours", first_hours), ("second_hours", second_hours)):
        values = np.asarray(hours)
        # Accept only whole hours of the day, so that each count has a bin.
        if values.size == 0:
            raise ValueError(f"{name} is empty.")
        if (
            not np.issubdtype(values.dtype, np.integer)
            or ((values < 0) | (values > 23)).any()
        ):
            raise ValueError(f"{name} must hold integer hours from 0 to 23.")
        groups.append(values)
    if n_permutations < 1:
        raise ValueError("n_permutations must be at least 1.")

    def overlap_of(first, second):
        """Return the overlap of the hour profiles of two arrays of hours.

        Parameters
        ----------
        first, second : numpy.ndarray of int
            Hours from 0 to 23.

        Returns
        -------
        float
            Sum over the hours of the smaller of the two shares.
        """
        first_shares = np.bincount(first, minlength=24) / first.size
        second_shares = np.bincount(second, minlength=24) / second.size
        return np.minimum(first_shares, second_shares).sum()

    observed = overlap_of(groups[0], groups[1])

    # Shuffle the pooled hours and split them again into two groups of the
    # original sizes. The seeded generator makes the shuffles repeatable.
    pooled = np.concatenate(groups)
    first_size = groups[0].size
    rng = np.random.default_rng(seed)
    shuffled_overlaps = np.empty(n_permutations)
    for index in range(n_permutations):
        order = rng.permutation(pooled.size)
        shuffled_overlaps[index] = overlap_of(
            pooled[order[:first_size]], pooled[order[first_size:]]
        )

    # Count the observed labels as one of the shuffles, so that the
    # p-value is never 0. The tolerance keeps a shuffle with the same
    # counts as the observed one from missing by a rounding error.
    at_most_observed = int((shuffled_overlaps <= observed + OVERLAP_TOLERANCE).sum())
    return {
        "overlap": float(observed),
        "p_value": (at_most_observed + 1) / (n_permutations + 1),
        "n_permutations": int(n_permutations),
    }
