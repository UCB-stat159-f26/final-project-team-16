"""Check the shared local clock used for traffic records."""

import pandas as pd
import pytest

from bpdtools.traffic import load_collisions, load_stops


def test_stop_during_repeated_hour(tmp_path):
    """Preserve the local clock and a zero-prefixed identifier."""
    path = tmp_path / "stops.csv"
    path.write_text("LEA_Record_ID,StopDate,StopTime\n001,11/03/2024,01:30\n")
    stops = load_stops(path)
    assert stops.loc[0, "LEA_Record_ID"] == "001"
    assert stops.loc[0, "local_time"] == pd.Timestamp("2024-11-03 01:30")


def test_collision_local_clock_and_blank_date(tmp_path):
    """Use local columns across midnight and keep a collision with no date."""
    path = tmp_path / "collisions.csv"
    path.write_text(
        "Date,Time,DateTime\n2022-01-01,19:38:00,2022-01-02 03:38:00\n,12:00:00,\n"
    )
    collisions = load_collisions(path)
    assert len(collisions) == 2
    assert collisions.loc[0, "local_time"] == pd.Timestamp("2022-01-01 19:38")
    assert pd.isna(collisions.loc[1, "local_time"])


@pytest.mark.parametrize(
    ("loader", "date_column", "missing_column"),
    [(load_stops, "StopDate", "StopTime"), (load_collisions, "Date", "Time")],
)
def test_missing_time_column(tmp_path, loader, date_column, missing_column):
    """Identify the missing column when the schema is incomplete."""
    path = tmp_path / "events.csv"
    path.write_text(date_column + "\n")
    with pytest.raises(KeyError, match=missing_column):
        loader(path)
