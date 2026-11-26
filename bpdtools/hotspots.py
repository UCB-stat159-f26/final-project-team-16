"""Count calls by block address and measure how concentrated they are.

block_counts counts calls per block, busiest first.
"""

from bpdtools.sectors import normalize_block_address

# Column of block addresses in the calls of load_calls.
ADDRESS_COLUMN = "Block Address"

# Names of the result index and of the result Series of block_counts.
BLOCK_INDEX_NAME = "block"
COUNT_NAME = "count"


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
