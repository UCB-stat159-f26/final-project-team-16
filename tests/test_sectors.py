"""Tests for bpdtools.sectors."""

import pandas as pd
import pytest

from bpdtools.sectors import normalize_block_address


def test_normalize_block_address_collapses_spaces_and_upper_cases():
    """Check that extra spaces go and the letters become upper case."""
    # Raw forms with spaces at the ends and doubled spaces or a tab inside.
    addresses = pd.Series(["  2400  telegraph Ave ", "1900\toxford ST"])
    result = normalize_block_address(addresses)
    assert result.tolist() == ["2400 TELEGRAPH AVE", "1900 OXFORD ST"]


def test_normalize_block_address_sorts_the_streets_of_an_intersection():
    """Check that both street orders give one key and a stray "&" is dropped."""
    # The same corner in two orders, one without spaces around "&", and an
    # address that ends with a stray "&".
    addresses = pd.Series(
        [
            "PARKER ST & MILVIA ST",
            "milvia st&parker st",
            "2400 TELEGRAPH AVE &",
        ]
    )
    result = normalize_block_address(addresses)
    assert result.tolist() == [
        "MILVIA ST & PARKER ST",
        "MILVIA ST & PARKER ST",
        "2400 TELEGRAPH AVE",
    ]


def test_normalize_block_address_keeps_blank_and_missing_values_missing():
    """Check that empty, all-space, "&"-only, and missing addresses give NaN."""
    # A custom index, which the result must keep.
    addresses = pd.Series(
        ["", "   ", " & ", None, "1900 oxford st"], index=[7, 8, 9, 10, 11]
    )
    result = normalize_block_address(addresses)
    assert result.index.tolist() == [7, 8, 9, 10, 11]
    assert result.isna().tolist() == [True, True, True, True, False]
    assert result.loc[11] == "1900 OXFORD ST"


def test_normalize_block_address_rejects_numbers():
    """Check that a number in place of an address raises a TypeError."""
    # A table read without dtype=str can hold numbers.
    with pytest.raises(TypeError, match="dtype=str"):
        normalize_block_address(pd.Series(["1900 OXFORD ST", 2400]))
