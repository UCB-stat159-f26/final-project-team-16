"""Count calls by block address and measure how concentrated they are.

block_counts counts calls per block, busiest first.
top_share gives the share of all calls in the busiest blocks.
yearly_top_overlap compares the busiest blocks of consecutive years.
"""

import math

import pandas as pd

from bpdtools.sectors import normalize_block_address

# Column of block addresses in the calls of load_calls.
ADDRESS_COLUMN = "Block Address"

# Names of the result index and of the result Series of block_counts.
BLOCK_INDEX_NAME = "block"
COUNT_NAME = "count"

# Columns of the table that top_share returns, in order.
SHARE_COLUMNS = ("fraction", "n_blocks", "n_calls", "share")

# Columns of the table of year pairs that yearly_top_overlap returns, in order.
OVERLAP_COLUMNS = ("year", "next_year", "n_top", "n_top_next", "n_shared")


def block_counts(events, address_column=ADDRESS_COLUMN):
    """Count events per block address, busiest block first.

    Addresses are matched with the keys of
    `bpdtools.sectors.normalize_block_address`, so "2700 Channing Way" and
    "2700 CHANNING  WAY" count as one block, and "A ST & B ST" and
    "B ST & A ST" as one intersection.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `address_column`.
    address_column : str, default "Block Address"
        Name of the column that holds the block address of each event as
        text.

    Returns
    -------
    pandas.Series
        Integer counts named "count", indexed by the block key, named
        "block". Blocks are sorted by count, largest first; blocks with the
        same count are sorted by key, so the order is the same on every
        run. Events whose address is missing or blank are not counted.

    Raises
    ------
    KeyError
        If `address_column` is not a column of `events`.
    TypeError
        If an address that is not missing is not text.
    """
    # Stop with a clear message when the address column is missing.
    if address_column not in events.columns:
        raise KeyError(
            f"events has no column {address_column!r}. Its columns are "
            f"{list(events.columns)}; pass one of these names."
        )

    # Use the same address keys as the sector lookup, so that one block
    # written in two ways counts once. A blank address gets no key.
    keys = normalize_block_address(events[address_column]).dropna()

    # Count each key, then sort: largest count first, and by key within a
    # count, so that ties come out in the same order on every run.
    counts = keys.value_counts().rename_axis(BLOCK_INDEX_NAME).rename(COUNT_NAME)
    order = counts.reset_index().sort_values(
        [COUNT_NAME, BLOCK_INDEX_NAME], ascending=[False, True]
    )
    counts = order.set_index(BLOCK_INDEX_NAME)[COUNT_NAME]
    return counts.astype("int64")


def top_share(counts, fractions):
    """Give the share of all calls in the busiest blocks.

    Parameters
    ----------
    counts : pandas.Series
        Calls per block, as returned by `block_counts`: busiest block
        first.
    fractions : sequence of float
        Fractions of the blocks to take from the top, each above 0 and at
        most 1, such as (0.01, 0.05, 0.10).

    Returns
    -------
    pandas.DataFrame
        One row per fraction, with the columns `fraction`, `n_blocks`,
        `n_calls`, and `share`. `n_blocks` is the fraction of all blocks
        rounded to a whole block, and at least one block. `n_calls` is the
        number of calls in these blocks, and `share` is `n_calls` divided by
        all calls. Blocks that tie at the cutoff have the same count, so
        the share does not depend on which of them is taken.

    Raises
    ------
    ValueError
        If `counts` holds no calls, or if a fraction is not above 0 and at
        most 1.
    """
    # A share needs at least one call to divide by.
    total_calls = int(counts.sum())
    if total_calls == 0:
        raise ValueError("counts holds no calls, so no share can be given.")

    # Sort again, so that the result is right even when counts is not
    # sorted yet.
    sorted_counts = counts.sort_values(ascending=False)
    n_all_blocks = len(sorted_counts)

    rows = []
    for fraction in fractions:
        if not 0 < fraction <= 1:
            raise ValueError(
                f"fraction {fraction!r} is not above 0 and at most 1; pass "
                "a fraction of the blocks, such as 0.05 for 5%."
            )
        # Round to a whole block. A fraction smaller than one block still
        # takes the busiest block. Python's round() goes to the even number
        # at .5, so floor(x + 0.5) is used to round .5 up.
        n_blocks = max(1, math.floor(fraction * n_all_blocks + 0.5))
        n_calls = int(sorted_counts.iloc[:n_blocks].sum())
        rows.append((fraction, n_blocks, n_calls, n_calls / total_calls))
    return pd.DataFrame(rows, columns=list(SHARE_COLUMNS))


def yearly_top_overlap(events, time_column, n_top, address_column=ADDRESS_COLUMN):
    """Compare the busiest blocks of each year with those of the next year.

    The top blocks of a year are the `n_top` blocks with the most calls in
    that year. A block that ties with the last of them is also a top block,
    so a year can have more than `n_top` top blocks; leaving it out would
    let the order of the block names decide.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per event. Must contain `time_column` and `address_column`.
    time_column : str
        Name of a tz-naive datetime64 column with the local time of each
        event, such as `local_time` of `load_calls`.
    n_top : int
        Number of top blocks to compare in each year, at least 1.
    address_column : str, default "Block Address"
        Name of the column that holds the block address of each event.

    Returns
    -------
    pairs : pandas.DataFrame
        One row per pair of consecutive years with events, with the columns
        `year`, `next_year`, `n_top` and `n_top_next` (the number of top
        blocks of each year, ties included), and `n_shared` (the number of
        blocks that are top blocks in both years).
    every_year : list of str
        Block keys that are top blocks in every year, sorted.

    Raises
    ------
    KeyError
        If `time_column` or `address_column` is not a column of `events`.
    TypeError
        If `time_column` is not tz-naive datetime64.
    ValueError
        If `n_top` is smaller than 1.
    """
    if n_top < 1:
        raise ValueError(f"n_top is {n_top!r}; pass at least 1.")
    if time_column not in events.columns:
        raise KeyError(
            f"events has no column {time_column!r}. Its columns are "
            f"{list(events.columns)}; pass one of these names."
        )
    if not pd.api.types.is_datetime64_dtype(events[time_column]):
        raise TypeError(
            f"{time_column!r} has dtype {events[time_column].dtype}; it must "
            "be tz-naive datetime64 in local time."
        )

    # Top blocks of each year: count the calls of that year per block, and
    # keep every block with at least the count of the n_top-th block.
    years = events[time_column].dt.year
    top_by_year = {}
    for year in sorted(years.dropna().unique()):
        counts = block_counts(events.loc[years == year], address_column)
        if counts.empty:
            continue
        cutoff = counts.iloc[min(n_top, len(counts)) - 1]
        top_by_year[int(year)] = set(counts.index[counts >= cutoff])

    # Compare each year with the next year that has calls.
    ordered = sorted(top_by_year)
    rows = [
        (
            year,
            next_year,
            len(top_by_year[year]),
            len(top_by_year[next_year]),
            len(top_by_year[year] & top_by_year[next_year]),
        )
        for year, next_year in zip(ordered, ordered[1:])
    ]
    pairs = pd.DataFrame(rows, columns=list(OVERLAP_COLUMNS))

    # Blocks that are top blocks in every year.
    every_year = sorted(set.intersection(*top_by_year.values())) if top_by_year else []
    return pairs, every_year
