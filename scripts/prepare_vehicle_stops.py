"""Build the event-level vehicle-stop table from the BPD stop snapshot.

Run from the project root with python3 scripts/prepare_vehicle_stops.py.
Source date, time, and coordinate strings are preserved for downstream use.
"""
import csv
from pathlib import Path

FIELDS = ("LEA_Record_ID", "TypeOfStopDesc", "StopDate", "StopTime", "Latitude", "Longitude")


def vehicle_stops(rows):
    """Return vehicle events keyed by ID from an iterable of BPD row dictionaries.

    Each value is a dictionary of event fields. Missing IDs or conflicting
    event fields within an ID raise ValueError. Missing coordinates are kept.
    """
    events = {}
    for row in rows:
        record = {field: row[field] for field in FIELDS}
        key = record["LEA_Record_ID"]
        if not key or not key.strip():
            raise ValueError("Missing stop ID")
        # Verify agreement before keeping one record for all people in a stop.
        if key in events and events[key] != record:
            raise ValueError(f"Inconsistent event fields for stop ID {key}")
        events[key] = record
    return {k: v for k, v in events.items() if v["TypeOfStopDesc"] == "Vehicular Stop"}


def main():
    """Read the raw CSV and write data/processed/vehicle_stops.csv."""
    with Path("data/raw/stop_data.csv").open(encoding="utf-8-sig", newline="") as source:
        events = vehicle_stops(csv.DictReader(source))
    output = Path("data/processed/vehicle_stops.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as dest:
        writer = csv.DictWriter(dest, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(events.values())
    print(f"{len(events):,} vehicle stops -> {output}")


if __name__ == "__main__":
    main()
