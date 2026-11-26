"""Tests for bpdtools.hotspots."""

import pandas as pd
import pytest

from bpdtools.hotspots import block_counts


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
