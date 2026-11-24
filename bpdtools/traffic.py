"""Load the shared vehicle-stop and collision snapshots for analysis."""

import pandas as pd

from bpdtools.paths import repo_path


def load_stops(path=None):
    """Read vehicle stops and combine the local stop date and time.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        Input CSV. Defaults to the shared vehicle_stops.csv snapshot.

    Returns
    -------
    pandas.DataFrame
        Original columns with StopDate parsed, plus a timezone-naive local_time.
        A missing date or time leaves local_time missing.

    Raises
    ------
    FileNotFoundError
        If the input file is missing.
    KeyError
        If StopDate or StopTime is missing.
    ValueError
        If a nonmissing date or timestamp cannot be parsed.
    """
    # Use the shared snapshot by default and keep stop identifiers as text.
    if path is None:
        path = repo_path("data", "processed", "vehicle_stops.csv")
    stops = pd.read_csv(
        path,
        dtype={"LEA_Record_ID": "string", "StopDate": "string", "StopTime": "string"},
    )

    # Preserve the wall clock even during the repeated hour at the end of DST.
    stops["local_time"] = pd.to_datetime(
        stops["StopDate"] + " " + stops["StopTime"], format="%m/%d/%Y %H:%M"
    )
    stops["StopDate"] = pd.to_datetime(stops["StopDate"], format="%m/%d/%Y")
    return stops


def load_collisions(path=None):
    """Read collisions and combine the local date and time.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        Input CSV. Defaults to the shared collisions.csv snapshot.

    Returns
    -------
    pandas.DataFrame
        Original columns with Date parsed, plus a timezone-naive local_time.
        A missing date or time leaves local_time missing.

    Raises
    ------
    FileNotFoundError
        If the input file is missing.
    KeyError
        If Date or Time is missing.
    ValueError
        If a nonmissing date or timestamp cannot be parsed.
    """
    # Keep undated collision records for analyses that only need location.
    if path is None:
        path = repo_path("data", "processed", "collisions.csv")
    collisions = pd.read_csv(path, dtype={"Date": "string", "Time": "string"})

    # Date and Time follow the Berkeley clock. The separate DateTime field is UTC.
    collisions["local_time"] = pd.to_datetime(
        collisions["Date"] + " " + collisions["Time"], format="%Y-%m-%d %H:%M:%S"
    )
    collisions["Date"] = pd.to_datetime(collisions["Date"], format="%Y-%m-%d")
    return collisions
