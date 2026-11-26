"""Tests for bpdtools.hotspots."""

import pandas as pd
import pytest

from bpdtools.hotspots import block_counts, top_share, yearly_top_overlap


def small_calls():
    """Build six calls on three blocks, written in different ways.

    Returns
    -------
    pandas.DataFrame
        Column `Block Address` (text). Three calls are on 2700 Channing Way
        in upper and lower case, two on one intersection written in both
        orders, and one on 100 Oak St.
    """
    return pd.DataFrame(
        {
            "Block Address": [
                "2700 CHANNING WAY",
                "2700 Channing  Way",
                " 2700 channing way ",
                "A ST & B ST",
                "B ST & A ST",
                "100 OAK ST",
            ]
        }
    )


def test_block_counts_counts_one_block_written_in_different_ways_once():
    """Check that case, spaces, and street order do not split a block."""
    counts = block_counts(small_calls())
    assert counts.to_dict() == {
        "2700 CHANNING WAY": 3,
        "A ST & B ST": 2,
        "100 OAK ST": 1,
    }


def test_block_counts_puts_the_busiest_block_first_and_ties_by_name():
    """Check the order: largest count first, then the key for a tie."""
    calls = pd.DataFrame({"Block Address": ["300 C ST", "100 A ST", "200 B ST"]})
    counts = block_counts(calls)
    assert counts.index.tolist() == ["100 A ST", "200 B ST", "300 C ST"]
    assert counts.tolist() == [1, 1, 1]


def test_block_counts_skips_missing_and_blank_addresses():
    """Check that a call without a usable address is not counted."""
    calls = pd.DataFrame({"Block Address": ["100 OAK ST", None, "   ", "&"]})
    counts = block_counts(calls)
    assert counts.to_dict() == {"100 OAK ST": 1}


def test_block_counts_names_the_index_and_the_series():
    """Check the names "block" and "count" and the integer type."""
    counts = block_counts(small_calls())
    assert counts.name == "count"
    assert counts.index.name == "block"
    assert counts.dtype == "int64"


def test_block_counts_returns_an_empty_series_for_an_empty_table():
    """Check that a table with no rows gives an empty Series."""
    calls = pd.DataFrame({"Block Address": pd.Series([], dtype="str")})
    counts = block_counts(calls)
    assert counts.empty
    assert counts.name == "count"


def test_block_counts_names_a_missing_address_column():
    """Check that a missing column raises a KeyError with its name."""
    with pytest.raises(KeyError, match="Address"):
        block_counts(pd.DataFrame({"other": ["100 OAK ST"]}))


def test_block_counts_leaves_the_input_unchanged():
    """Check that the table is the same before and after the call."""
    calls = small_calls()
    before = calls.copy(deep=True)
    block_counts(calls)
    pd.testing.assert_frame_equal(calls, before)


def ten_blocks():
    """Build calls per block for ten blocks with 100 calls in all.

    Returns
    -------
    pandas.Series
        Counts 30, 20, 10, 10, 10, 5, 5, 5, 3, 2 on blocks "b0" to "b9",
        busiest first, as block_counts returns them.
    """
    return pd.Series(
        [30, 20, 10, 10, 10, 5, 5, 5, 3, 2],
        index=pd.Index([f"b{i}" for i in range(10)], name="block"),
        name="count",
    )


def test_top_share_gives_the_share_of_the_busiest_blocks():
    """Check 10%, 20%, and 50% of ten blocks: one, two, and five blocks."""
    shares = top_share(ten_blocks(), [0.1, 0.2, 0.5])
    assert shares["n_blocks"].tolist() == [1, 2, 5]
    assert shares["n_calls"].tolist() == [30, 50, 80]
    assert shares["share"].tolist() == pytest.approx([0.3, 0.5, 0.8])


def test_top_share_takes_at_least_one_block():
    """Check that a fraction smaller than one block takes the busiest block."""
    shares = top_share(ten_blocks(), [0.01])
    assert shares["n_blocks"].tolist() == [1]
    assert shares["share"].tolist() == pytest.approx([0.3])


def test_top_share_does_not_depend_on_which_tied_block_is_taken():
    """Check a cutoff inside a tie: three blocks have 10 calls, 40% takes two."""
    counts = ten_blocks()
    # Swap the names of two tied blocks; the share must stay the same.
    swapped = counts.rename(index={"b2": "b4", "b4": "b2"})
    assert top_share(counts, [0.4])["share"].tolist() == pytest.approx([0.7])
    assert top_share(swapped, [0.4])["share"].tolist() == pytest.approx([0.7])


def test_top_share_sorts_counts_that_are_not_sorted():
    """Check that the busiest blocks are found in any order."""
    shuffled = ten_blocks().iloc[::-1]
    assert top_share(shuffled, [0.1])["n_calls"].tolist() == [30]


def test_top_share_rejects_a_fraction_outside_zero_and_one():
    """Check that 0 and 1.5 raise a ValueError."""
    for fraction in (0, 1.5):
        with pytest.raises(ValueError, match="fraction"):
            top_share(ten_blocks(), [fraction])


def test_top_share_rejects_counts_without_calls():
    """Check that empty counts raise a ValueError."""
    empty = pd.Series([], dtype="int64", name="count")
    with pytest.raises(ValueError, match="no calls"):
        top_share(empty, [0.1])


def three_years():
    """Build calls on four blocks over 2021, 2022, and 2023.

    Returns
    -------
    pandas.DataFrame
        Columns `local_time` (tz-naive datetime64) and `Block Address`
        (text). With n_top=2, the top blocks are {A, B} in 2021, {A, C} in
        2022, and {A, B, D} in 2023, where B and D tie for second place.
    """
    rows = [
        ("2021-03-01", "100 A ST", 3),
        ("2021-03-01", "200 B ST", 2),
        ("2021-03-01", "300 C ST", 1),
        ("2022-05-01", "100 A ST", 4),
        ("2022-05-01", "300 C ST", 3),
        ("2022-05-01", "200 B ST", 1),
        ("2023-07-01", "100 A ST", 5),
        ("2023-07-01", "200 B ST", 2),
        ("2023-07-01", "400 D ST", 2),
    ]
    records = [(day, block) for day, block, n in rows for _ in range(n)]
    calls = pd.DataFrame(records, columns=["local_time", "Block Address"])
    calls["local_time"] = pd.to_datetime(calls["local_time"])
    return calls


def test_yearly_top_overlap_counts_shared_top_blocks_of_next_years():
    """Check the pairs 2021-2022 and 2022-2023 with n_top=2."""
    pairs, _ = yearly_top_overlap(three_years(), "local_time", n_top=2)
    assert pairs["year"].tolist() == [2021, 2022]
    assert pairs["next_year"].tolist() == [2022, 2023]
    # 2023 has three top blocks, because B and D tie for second place.
    assert pairs["n_top"].tolist() == [2, 2]
    assert pairs["n_top_next"].tolist() == [2, 3]
    # 2021-2022 share A; 2022-2023 share only A.
    assert pairs["n_shared"].tolist() == [1, 1]


def test_yearly_top_overlap_lists_the_blocks_on_top_every_year():
    """Check that only block A is a top block in all three years."""
    _, every_year = yearly_top_overlap(three_years(), "local_time", n_top=2)
    assert every_year == ["100 A ST"]


def test_yearly_top_overlap_rejects_n_top_below_one():
    """Check that n_top=0 raises a ValueError."""
    with pytest.raises(ValueError, match="n_top"):
        yearly_top_overlap(three_years(), "local_time", n_top=0)


def test_yearly_top_overlap_rejects_text_times():
    """Check that times stored as text raise a TypeError."""
    calls = three_years()
    calls["local_time"] = calls["local_time"].astype(str)
    with pytest.raises(TypeError, match="tz-naive"):
        yearly_top_overlap(calls, "local_time", n_top=2)
