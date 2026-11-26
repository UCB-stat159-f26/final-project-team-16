"""Count calls by block address and measure how concentrated they are.

block_counts counts calls per block, busiest first.
top_share gives the share of all calls in the busiest blocks.
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
