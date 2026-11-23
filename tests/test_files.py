"""Tests for bpdtools.files."""

import hashlib

import pandas as pd

from bpdtools.files import file_sha256, write_gzip_csv


def make_small_table():
    """Make a small text table for the tests.

    Returns
    -------
    pandas.DataFrame
        Three rows with an ID, a non-ASCII address, and a blank cell.
    """
    # Text values only, with one accented letter and one blank cell.
    return pd.DataFrame(
        {
            "id": ["2024-00000001", "2024-00000002", "2024-00000003"],
            "address": ["2400 DURANT AVE", "CAF\u00c9 ROW", ""],
        }
    )


def test_write_gzip_csv_gives_the_same_bytes_twice(tmp_path):
    """Check that two writes of one table give identical files."""
    # Write the same table to two different file names.
    first = tmp_path / "first.csv.gz"
    second = tmp_path / "second.csv.gz"
    write_gzip_csv(make_small_table(), first)
    write_gzip_csv(make_small_table(), second)
    assert first.read_bytes() == second.read_bytes()


def test_write_gzip_csv_returns_the_sha256_of_the_file(tmp_path):
    """Check that the returned checksum equals hashlib on the written bytes."""
    # Write the table, then hash the bytes on disk in two ways.
    path = tmp_path / "table.csv.gz"
    returned = write_gzip_csv(make_small_table(), path)
    expected = hashlib.sha256(path.read_bytes()).hexdigest()
    assert returned == expected
    assert file_sha256(path) == expected


def test_write_gzip_csv_round_trip_reads_back_the_table(tmp_path):
    """Check that reading the file as text gives back the same table."""
    # Write the table, then read it back with pandas.
    path = tmp_path / "table.csv.gz"
    write_gzip_csv(make_small_table(), path)
    # Read every cell as text and keep blank cells as empty strings.
    result = pd.read_csv(path, dtype=str, keep_default_na=False)
    pd.testing.assert_frame_equal(result, make_small_table())


def test_file_sha256_matches_hashlib_on_a_small_file(tmp_path):
    """Check file_sha256 on a small file against hashlib.sha256 of its bytes."""
    # A two-line file with known bytes.
    path = tmp_path / "small.txt"
    path.write_bytes(b"Incident Number\n2024-00000001\n")
    assert file_sha256(path) == hashlib.sha256(path.read_bytes()).hexdigest()
