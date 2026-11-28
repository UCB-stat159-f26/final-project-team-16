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

## Snapshot coverage and locations

These endpoints describe records with a local date. They do not establish uninterrupted daily reporting.

| File | First local date | Last local date | Missing local date | Both coordinates present |
|---|---|---|---:|---:|
| `processed/collisions.csv` | 2007-12-03 | 2026-11-01 | 101 | 16,638 / 16,639 |
| `processed/vehicle_stops.csv` | 2024-01-01 | 2026-05-26 | 0 | 7,385 / 7,431 |
| `raw/collision_data.csv` | 2007-12-03 | 2026-11-01 | 101 | 16,638 / 16,639 |
| `raw/stop_data.csv` | 2024-01-01 | 2026-05-26 | 0 | 10,844 / 10,931 |

Only two dated collision records precede 2011 (one in 2007 and one in 2010). The planned A1 trend starts in 2011.

For local-day and hourly collision analyses, use `Date`, `Time`, and `Hour` (America/Los_Angeles). The source `DateTime` represents UTC and can fall on the following calendar day. Report exclusions for missing dates or times in the relevant analysis.

Recorded collision times before 06:00 appear unreliable. This check uses the local time of day: `DateTime` converted from UTC to America/Los_Angeles, which matches `Time` in every record that has both. No record has a local time from 00:00 to 00:59, all 46 records at 01:xx have minutes 00 to 09, and 48% of the records from 01:00 to 05:59 have minutes under 10, against 20% from 06:00 to 19:59. The pattern appears in every year and in both fields, so the preparation script does not cause it. The source of the pattern is not known. Vehicle-stop times do not show it. When a result compares collision hours, also report the same result for 06:00 to 23:59 only.

Vehicle stops retain latitude and longitude in degrees. Collisions have an accident-location label and projected Web Mercator coordinates (`x`, `y`). Before assigning police beats, transform points and boundaries to the same coordinate system and report unmatched points. Coordinate presence alone does not establish a valid Berkeley location.

### Raw snapshot SHA-256

- `collision_data.csv` — `721eb3da422811cbbf48465adedccf2b07dd5660bf419191a3414492674043e5`
- `stop_data.csv` — `52eecf738f2021dc2fd165903db691d48a6bac17b25dfa45b7a37e0ba95938b3`

### Interpreting two abbreviated DUI labels

The primary A4 flag follows the wording of the recorded PCF description.
Two abbreviations warrant a sensitivity check. Of 19 passenger-for-hire
records labeled VC 23152(e), 17 predate July 1, 2018, one is undated, and
one is dated January 4, 2019. The passenger-for-hire BAC provision became
operative on July 1, 2018. The other abbreviated label, VC 23153(g), occurs
once on April 16, 2019 and refers to combined alcohol and drug impairment.

Both labels remain unclear under the primary text-only definition. Counting
the two 2019 records supported by the dated subsections would give 959
rather than 957 flags across the snapshot. Neither addition falls in Fall
2024. A PCF flag describes police coding, not a measured BAC.

Sources: [California AB 2687, chaptered text](https://www.leginfo.ca.gov/pub/15-16/bill/asm/ab_2651-2700/ab_2687_bill_20160928_chaptered.pdf)
and [CHP subsection history](https://www.chp.ca.gov/siteassets/files/idtf-trd-12-11-2019-dui-subsection-changes-history.pdf).

## Stop, collision and calendar codebooks

- [Vehicle stops](codebooks/vehicle_stops.md)
- [Collisions](codebooks/collisions.md)
- [Academic and event calendar](codebooks/calendar.md)
