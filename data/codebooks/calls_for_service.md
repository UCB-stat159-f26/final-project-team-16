# Codebook: Calls for Service, 2021-2025

## Source

- Dataset: Berkeley PD Calls for Service, 2019 - Current (CSV).
- Agency: Berkeley Police Department, published on the BPD Transparency Hub.
- Download URL: <https://www.arcgis.com/sharing/rest/content/items/272dfb0d5c5144679368fb2f97422a35/data>
- Downloaded: 2026-11-23 09:35 Pacific time (PST).
- Raw file: `data/downloads/calls_for_service.csv`. Git ignores this file,
  because it is about 58 MB and the publisher updates it every day.
- Raw file size: 58,519,130 bytes.
- Raw file SHA-256: `8714e2caff2edb6b7faed6d38db86dfa9c8b9e75672f7f4bd93bd5f257990b63`
- Raw rows: 360,889 (12 columns). The first local date is 2021-01-01, not a
  date in 2019, and the last record is from 2026-11-22.

## How the data is produced

Each row is one call for service from the BPD computer-aided dispatch (CAD)
system. A call starts when a person calls by phone or online, or when an
officer starts an activity (for example a traffic stop or a security check).
The table has no coordinates. The location is a block address or an
intersection, and a ZIP Code.

`scripts/prepare_calls.py` builds the processed table from the raw file:

1. It reads every cell as text with `bpdtools.calls.read_raw_calls`.
2. It finds the local date of each call with `bpdtools.calls.local_dates`.
3. It keeps the calls with a local date from 2021-01-01 to 2025-12-31.
4. It checks the dates, the `Incident Number` key, and the Call Type labels.
5. It sorts the rows and writes them with `bpdtools.files.write_gzip_csv`.

## Processed table

- File: `data/processed/calls_2021_2025.csv.gz` (gzip CSV, UTF-8, LF line
  ends, no index).
- Rows: 307,628, one row per call.
- Size: 4,763,460 bytes.
- SHA-256: `5e44a38168051493030e7e99f6f4410adb18ad936c937ee9e5e6e0d1679b56a3`
  (built from the raw file above).
- Sort order: `CreateDatetime` as text, then `Incident Number`.

The script drops these raw columns: the unnamed first column (a saved row
index), `Progress`, `Priority`, `Dispositions`, `City` (always BERKELEY),
and `NonBerkeley Address`.

## Columns

Every column is text. Read the file with
`pd.read_csv(path, dtype=str, keep_default_na=False)` and parse `date` when
you need dates.

| Column | Meaning | Type | Example values | Missing values |
|---|---|---|---|---|
| `Incident Number` | ID of the call, `YYYY-NNNNNNNN` | str | `2021-00000005` | None. Unique in the table |
| `CreateDatetime` | Time the call was created, local time with its UTC offset, as in the source | str | `2021-01-01 00:03:50-08:00` | None |
| `date` | Local calendar date in `America/Los_Angeles` | str, `YYYY-MM-DD` | `2021-01-01` | None |
| `Call Type` | Type of call, `CFS <code> - <description>` (137 labels) | str | `CFS 415 - Disturbance` | None |
| `Source` | How the call came in | str | `Telephone`, `Officer Initiated`, `911 Call`, `OnLine` | 32 blank |
| `Block Address` | Block or intersection, spelled as in the source (not normalized) | str | `1400 UNIVERSITY AVE` | None |
| `ZIP Code` | ZIP Code of the address (14 distinct values) | str, 5 digits | `94704` | 1,029 blank |

## Rules

- Time zone: `CreateDatetime` already holds local time with its offset:
  `-07:00` in 205,660 rows (daylight saving time) and `-08:00` in 101,968
  rows. `local_dates` parses each offset, converts the time to
  `America/Los_Angeles`, and keeps the date. It never shifts by a fixed
  number of hours. For every row, `date` equals the first 10 characters of
  `CreateDatetime`, and the script checks this.
- Window: a call is kept when its local date is from 2021-01-01 to
  2025-12-31, both included (`ANALYSIS_START` and `ANALYSIS_END` in
  `bpdtools/config.py`).
- Duplicates: `Incident Number` is unique and never blank, so the script
  removes no rows as duplicates. It stops with an error if this changes.
- Call Type groups: `bpdtools/config.py` lists each group as exact, full
  `Call Type` labels. Match them exactly, never by substring:
  `CFS 415 - Disturbance` (27,094 calls) and `CFS 415F - Family Disturbance`
  are not noise calls, and `CFS 243E1 - Domestic Violence` is not in the
  battery group. Calls with `Source` equal to `Officer Initiated` stay in
  the table and in the groups.
- Covered days: a local date is a covered day when the full table, with all
  call types, has at least one call on that date. Use
  `bpdtools.calls.covered_days` on the `date` column of the unfiltered
  table. A day with calls but no noise call is a covered day with zero
  noise calls. All 1,826 days from 2021-01-01 to 2025-12-31 are covered.

## Counts that define the data

| Group | `Call Type` label | Calls, 2021-2025 |
|---|---|---:|
| Noise (`NOISE_CALL_TYPES`) | `CFS 415E - Noise Disturbance` | 11,588 |
| | `CFS LDRPT - Loud Report` | 1,105 |
| Battery (`BATTERY_CALL_TYPES`) | `CFS 242 - Battery` | 4,809 |
| | `CFS 243 - Serious Battery` | 242 |
| | `CFS 245 - Assault w/Deadly Weapon` | 344 |
| Reckless driving (`RECKLESS_CALL_TYPES`) | `CFS 23103 - Reckless Vehicle` | 2,549 |

The groups hold 12,693 noise calls, 5,395 battery calls, and 2,549
reckless driving calls.

Calls per year: 61,085 (2021), 61,851 (2022), 63,430 (2023), 61,312
(2024), and 59,950 (2025).

Of the 360,889 raw rows, the script leaves out 53,261:

- 82 rows with a blank `CreateDatetime`, because they cannot be dated.
- 53,179 rows with a local date after 2025-12-31.
- 0 rows with a local date before 2021-01-01.

## Limitations

- The table has no coordinates, and `Block Address` is not normalized. The
  same place can have more than one spelling.
- `CreateDatetime` is the time the CAD record was created, not the time of
  the event.
- The year in `Incident Number` is not always the local year. In 62 rows
  they differ: 60 calls from December 2021 to December 2025 carry the
  prefix of the next year, and two calls carry `1994-00034660` and
  `2007-00002902`. Date a call by `date`, not by `Incident Number`.
- The publisher can change older rows. A new download can give a different
  processed table if rows inside 2021-2025 change.
- The SHA-256 of the gzip file holds for the zlib library of the project
  environment. Another zlib build can compress the same rows to different
  bytes; then compare the decompressed CSV.

## How to rebuild

From the repository root, after `make env` has created the conda
environment:

```bash
make data
```

For this table, `make data` runs `python scripts/download_calls.py` and
then `python scripts/prepare_calls.py` inside the environment. It needs the
internet. To rebuild the table from a raw file that is already in
`data/downloads/`, run only `python scripts/prepare_calls.py`. A new
download has new rows after 2025-12-31, so its raw SHA-256 differs from the
value above.
