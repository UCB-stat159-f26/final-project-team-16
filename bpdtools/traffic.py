"""Load the shared vehicle-stop and collision snapshots for analysis."""

import pandas as pd

from bpdtools.paths import repo_path


def load_stops(path=None):
    """Read processed vehicle stops into a DataFrame with local StopDate values.

    The optional path overrides the project's vehicle_stops.csv. Each row
    represents one vehicular stop. Preserve the original record ID as text.
    """
    if path is None:
        path = repo_path("data", "processed", "vehicle_stops.csv")
    stops = pd.read_csv(path, dtype={"LEA_Record_ID": "string"})
    stops["StopDate"] = pd.to_datetime(stops["StopDate"], format="%m/%d/%Y")
    return stops


def load_collisions(path=None):
    """Read processed collisions into a DataFrame, retaining undated records.

    The optional path overrides the project's collisions.csv. Use the local
    Date column for calendar comparisons. Blank dates remain NaT.
    """
    if path is None:
        path = repo_path("data", "processed", "collisions.csv")
    collisions = pd.read_csv(path)
    collisions["Date"] = pd.to_datetime(collisions["Date"], format="%Y-%m-%d")
    return collisions
