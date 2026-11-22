# Berkeley Police Department data

We downloaded the following CSV snapshots on November 22, 2026.

| File | Source | Raw rows |
|---|---|---:|
| `raw/stop_data.csv` | [Berkeley PD Stop Data](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/datasets/078f7d987228453ca30cf7a99311d8de/about) | 10,931 |
| `raw/collision_data.csv` | [Berkeley PD Collision Data](https://bpd-transparency-initiative-berkeleypd.hub.arcgis.com/datasets/fcb1720b81844fed9d2212ffe2f35c74/explore) | 16,639 |

## Counting vehicle stops

A stop can have multiple person records. We select rows where `TypeOfStopDesc` is `Vehicular Stop` and count each `LEA_Record_ID` once.
In this snapshot, 7,603 qualifying rows represent 7,431 distinct stops.
Stop type, date, time, latitude, and longitude are consistent within each stop ID.
From the repository root, run `python3 scripts/prepare_vehicle_stops.py` to generate `data/processed/vehicle_stops.csv`, with one row per vehicle stop.

## Counting collisions

Each of the 16,639 rows has a distinct, nonmissing `ObjectId`.

For A4, we count collisions whose recorded primary collision factor explicitly mentions alcohol or a blood alcohol concentration threshold. The proposed classification covers all 137 PCF descriptions in the November 22 snapshot and flags 957 of 16,639 records. See `data/mappings/collision_pcf.csv` for the exact labels and rationale. Run `python3 scripts/prepare_collisions.py` from the repository root to reproduce the event table.