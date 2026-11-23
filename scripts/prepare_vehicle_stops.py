"""Build the event-level vehicle-stop table from the BPD stop snapshot.

Run from the project root with python3 scripts/prepare_vehicle_stops.py.
Source date, time, and coordinate strings are preserved for downstream use.
"""
import csv
from pathlib import Path

FIELDS = ("LEA_Record_ID", "TypeOfStopDesc", "StopDate", "StopTime", "Latitude", "Longitude")


def vehicle_stops(rows):
    """Collect one event record per vehicular stop.

    Parameters
    ----------
    rows : iterable of dict
        Person-level CSV records containing the fields listed in FIELDS.

    Returns
    -------
    dict of str to dict
        Stop IDs mapped to their event fields, including any missing coordinates.

    Raises
    ------
    ValueError
        If a stop ID is blank or its event fields disagree across person records.
    """
    events = {}
    for row in rows:
        # Keep the fields shared by everyone involved in the same stop.
        record = {field: row[field] for field in FIELDS}
        key = record["LEA_Record_ID"]
        # A blank ID cannot distinguish one stop from another.
        if not key or not key.strip():
            raise ValueError("Missing stop ID")
        # Verify agreement before keeping one record for all people in a stop.
        if key in events and events[key] != record:
            raise ValueError(f"Inconsistent event fields for stop ID {key}")
        events[key] = record
    # Filter after validation so conflicting stop types within an ID surface.
    return {k: v for k, v in events.items() if v["TypeOfStopDesc"] == "Vehicular Stop"}


def main():
    """Take no arguments, write the vehicle-stop CSV, and return None."""
    # Group the original person records before exporting event counts.
    with Path("data/raw/stop_data.csv").open(encoding="utf-8-sig", newline="") as source:
        events = vehicle_stops(csv.DictReader(source))
    # Export one row per stop in the column order used by the notebooks.
    output = Path("data/processed/vehicle_stops.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(events.values())
    print(f"{len(events):,} vehicle stops -> {output}")


if __name__ == "__main__":
    main()
