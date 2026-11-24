# Codebook: crime cases, 2021-2025

## Source

- Dataset: `cases_latlon`, the BPD crime cases layer with map points.
- Agency: Berkeley Police Department, published on the BPD Transparency Hub.
- Layer URL: <https://services7.arcgis.com/vIHhVXjE1ToSg0Fz/arcgis/rest/services/cases_latlon/FeatureServer/0>
- Downloaded: 2026-11-23, 09:37 to 09:40 Pacific time (PST).
- Raw file: `data/downloads/crime_cases.csv`. Git ignores this file, because
  the publisher updates the layer every day.
- Raw file size: 30,055,159 bytes.
- Raw file SHA-256: `2f4959300c06ec8dd367d33d0836f3e4da4d78079890d2e8e830c452feb4999b`
- Raw rows: 151,430 (15 columns), with 110,615 distinct `Case_Number`
  values.

## How the data is produced

BPD publishes one record for each statute in a case report. A case with
three statutes has three rows. The case fields (time, Incident Type,
address, and map point) repeat on every row of the case, and in the raw
file they agree within every case.

`scripts/download_crime_cases.py` reads the layer 1,000 records at a time,
ordered by `ObjectId`. It keeps every attribute field in layer order and
every value as the layer returns it. It stops if the number of records
differs from the count that the layer reports.

`scripts/prepare_crime_cases.py` builds the processed table from the raw
file:

1. It reads every cell as text with `bpdtools.crime.read_raw_cases`, which
   also replaces the no-point code `-361` in `lat` and `lon` with a missing
   value.
2. It converts `Occurred_Datetime` to local time with
   `bpdtools.crime.local_times_from_epoch`.
3. It keeps the rows with a local date from 2021-01-01 to 2025-12-31.
4. It keeps one row per case with `bpdtools.crime.one_row_per_case`.
5. It removes placeholder points with
   `bpdtools.crime.clear_placeholder_points`.
6. It sorts the cases and writes them with `bpdtools.files.write_gzip_csv`.

## Processed table

- File: `data/processed/crime_cases_2021_2025.csv.gz` (gzip CSV, UTF-8, LF
  line ends, no index).
- Rows: 51,418, one row per case.
- Size: 1,412,466 bytes.
- SHA-256: `e57cf0f2f34cb51f4d3cf2c48d2021967d4a7ed6e8d5d75a115cdafa2707d9cb`
  (built from the raw file above).
- Sort order: `Occurred_Datetime`, then `Case_Number`.

The script drops these raw columns: `Statute`, `Statute_Description`, and
`Statute_Type` (they describe one statute, and the table has one row per
case), `Case_Status` and `Disposition` (they change after the download),
`Full_Address` (a 0 or 1 flag, despite its name), `City` (always
BERKELEY), and `ObjectId` (the row number of the layer).

## Columns

Every column is text. Read the file with
`pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])`, and
convert `lat` and `lon` with `pd.to_numeric`.

| Column | Meaning | Type | Example values | Missing values |
|---|---|---|---|---|
| `Case_Number` | BPD case number, `YYYY-NNNNNNNN` | str | `2021-00006744` | None. Unique in the table |
| `Occurred_Datetime` | Local date and time when the crime occurred, in `America/Los_Angeles`, without an offset | str, `YYYY-MM-DD HH:MM:SS` | `2021-01-01 00:00:00` | None |
| `date` | Local occurred date, the first 10 characters of `Occurred_Datetime` | str, `YYYY-MM-DD` | `2021-01-01` | None |
| `Incident_Type` | BPD case type (38 labels) | str | `Assault/Battery Felony` | None |
| `Block_Address` | Block or intersection, spelled as in the source (not normalized) | str | `1700 DELAWARE ST` | 1,095 blank |
| `ZIP_Code` | ZIP Code of the address (13 distinct values) | str, 5 digits | `94703` | None |
| `lat` | Latitude of the map point, degrees (WGS 84) | str, decimal | `37.87377768547257` | 2,950 blank |
| `lon` | Longitude of the map point, degrees (WGS 84) | str, decimal | `-122.27653356148934` | 2,950 blank |

## Rules

- Time zone: the layer stores `Occurred_Datetime` as milliseconds since
  1970-01-01 00:00 UTC. `local_times_from_epoch` converts each value to
  `America/Los_Angeles` with the daylight saving time rules. It never shifts
  by a fixed number of hours. For example, 2024-12-26 06:25 UTC becomes
  2024-12-25 22:25 local time.
- Window: a case is kept when its local date is from 2021-01-01 to
  2025-12-31, both included (`ANALYSIS_START` and `ANALYSIS_END` in
  `bpdtools/config.py`).
- One row per case: count crime cases by `Case_Number`. The script keeps
  the first statute row of each case. It stops with an error if the rows
  of a case disagree on time, Incident Type, address, or map point.
- No-point code: the layer writes `-361` in `lat` and `lon` when a case has
  no map point. `read_raw_cases` turns it into a missing value, so that it
  is never read as a place. In the raw file, 4,312 rows have this code; in
  the window, 2,193 rows (1,095 cases). They are exactly the rows with a
  blank `Block_Address`.
- Placeholder point: the layer gives the point 37.87022021065617,
  -122.27285493558117 to many cases. It is the point of
  2100 MARTIN LUTHER KING JR WAY, the BPD headquarters. The script keeps
  this point only when the address, in upper case with single spaces, is
  exactly that address. For every other case at this point, `lat` and `lon`
  become missing, because the point is a placeholder, not the place of the
  case. The point and the address are `PLACEHOLDER_LAT`, `PLACEHOLDER_LON`,
  and `HEADQUARTERS_ADDRESS` in `bpdtools/config.py`.
- Assault cases: `ASSAULT_INCIDENT_TYPES` in `bpdtools/config.py` lists
  the exact, full `Incident_Type` labels. Match them exactly. Other labels,
  such as `Domestic violence` and the sexual assault labels, are not in the
  group.

## Counts that define the data

| Group | `Incident_Type` label | Cases, 2021-2025 |
|---|---|---:|
| Assault (`ASSAULT_INCIDENT_TYPES`) | `Assault/Battery Misdemeanor` | 2,631 |
| | `Assault/Battery Felony` | 936 |

The assault group holds 3,567 cases.

Cases per year: 9,214 (2021), 10,940 (2022), 11,662 (2023), 10,332
(2024), and 9,270 (2025).

Cases at the placeholder point, by year:

| Year | Point removed (other address) | Point kept (headquarters address) |
|---|---:|---:|
| 2021 | 635 | 191 |
| 2022 | 616 | 210 |
| 2023 | 544 | 232 |
| 2024 | 29 | 77 |
| 2025 | 31 | 76 |
| Total | 1,855 | 786 |

In the whole layer, all years together, 3,625 cases have the placeholder
point: 1,474 at the headquarters address and 2,151 at other addresses.

Missing points: 2,950 cases have no map point, 1,095 with the no-point code
and 1,855 with a removed placeholder point.

Of the 110,615 raw cases, the script leaves out 59,197:

- 1 case without an occurred time, because it cannot be dated.
- 50,943 cases with a local date before 2021-01-01.
- 8,253 cases with a local date after 2025-12-31.

## Match rates

The Hub's crime cases CSV export of 2026-11-20 stores local times without
an offset. For the 110,561 cases in both sources, the converted local time
equals the Hub time for 110,560 cases; the other case is `2024-00010955`
(see Limitations).
`Incident_Type` and `Block_Address` are equal for every common case.

## Limitations

- Repeated hour: `Occurred_Datetime` has no offset. On the first Sunday of
  November, clocks go back from 02:00 to 01:00, so a time from 01:00 to
  01:59 on that day can be either of two moments. This applies to 6 cases
  (4 on 2023-11-05, 1 on 2024-11-03, and 1 on 2025-11-02). Use `date` for
  these cases; the date is correct.
- Left-out case: case `2024-00010955` (`Outside Agency Report`) has no
  occurred time in the layer. The Hub's crime cases CSV export of
  2026-11-20 gives it the local time 2024-03-10 02:30:00. That time does
  not exist, because clocks skipped from 02:00 to 03:00 on that day. The
  case is not in the table.
- Unknown times: 2,134 cases have the time `00:00:00`. This time often
  means that the time of the crime is not known. Use `date` for these
  cases, not the hour.
- Placeholder rule: the address match is exact. Eleven cases in the window
  have the headquarters address in another spelling (for example
  `2100 MARTIN LUTHER KING JR WY`), so their correct point is removed. A
  case at the headquarters address keeps the point, also when the crime
  may have happened elsewhere; the table cannot tell these cases apart.
- Case number year: the year in `Case_Number` is not always the local year,
  because a case can be reported later. In 1,220 cases they differ. Date a
  case by `date`, not by `Case_Number`.
- The publisher can add a late report of an old crime or edit an old case.
  A new download can give a different processed table.
- The SHA-256 of the gzip file holds for the zlib library of the project
  environment. Another zlib build can compress the same rows to different
  bytes; then compare the decompressed CSV.

## How to rebuild

From the repository root, after `make env` has created the conda
environment:

```bash
make data
```

For this table, `make data` runs `python scripts/download_crime_cases.py`
and then `python scripts/prepare_crime_cases.py` inside the environment,
after the two Calls for Service scripts. It needs the internet. To rebuild
the table from a raw file that is already in `data/downloads/`, run only
`python scripts/prepare_crime_cases.py`. A new download has new cases, so
its raw SHA-256 differs from the value above.
