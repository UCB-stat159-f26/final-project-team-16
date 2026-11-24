# Codebook: block address to police beat sector lookup

`data/processed/address_sectors.csv` gives each block address one map point
and the police beat sector of that point. Calls for Service have a block
address but no map point, so they get their sector from this table.

## Source

- Address points: the raw crime cases download
  `data/downloads/crime_cases.csv`, all years. The layer was downloaded on
  2026-11-23, 09:37 to 09:40 Pacific time (PST). Size 30,055,159 bytes,
  SHA-256 `2f4959300c06ec8dd367d33d0836f3e4da4d78079890d2e8e830c452feb4999b`.
  See the [crime cases codebook](crime_cases.md).
- Beat polygons: `data/boundaries/police_beats.geojson`, 14 beats with the
  sectors 1 to 14, downloaded on 2026-11-22. SHA-256
  `9f15ab1e779c4d709fd5cf4f35c01b47b764066a48f8bb7c13e07e849bc4f389`. See
  [data/boundaries/README.md](../boundaries/README.md).
- The calls that use the table are described in the
  [Calls for Service codebook](calls_for_service.md).

## How the data is produced

`scripts/prepare_address_sectors.py` builds the table:

1. It reads every cell of the raw crime file as text with
   `bpdtools.crime.read_raw_cases`, which also replaces the no-point code
   `-361` in `lat` and `lon` with a missing value (151,430 rows, 110,615
   cases).
2. It keeps the first row of each `Case_Number` with
   `bpdtools.crime.one_row_per_case`, so that each case counts once.
3. It removes placeholder points with
   `bpdtools.crime.clear_placeholder_points` (the rule of the crime cases
   codebook).
4. It builds the table with `bpdtools.sectors.build_lookup`. This function
   makes the address key with `normalize_block_address`, leaves out cases
   without a key or a point and points outside the box 37.84 < lat < 37.91,
   -122.33 < lon < -122.22, takes the median longitude and the median
   latitude of the cases of each key, and gives the key the sector of this
   median point with `assign_sectors`.
5. It writes the rows sorted by `block_key`.

## Processed table

- File: `data/processed/address_sectors.csv` (CSV, UTF-8, LF line ends, no
  index).
- Rows: 2,913, one row per address key.
- Size: 221,882 bytes.
- SHA-256: `67512f50ef21aaecd2b1037422d81bd646855a23e8f59fcf4d64218e21744fe6`
  (built from the raw file and the beats file above).
- Sort order: `block_key`.

## Columns

| Column | Meaning | Type | Example |
|---|---|---|---|
| `block_key` | Address key from `normalize_block_address`. Unique. | str | `2400 DURANT AVE` |
| `n_cases` | Crime cases, all years, with this key and a point in the box | int | `703` |
| `lon` | Median longitude of these cases, degrees (WGS 84) | float | `-122.26029939982605` |
| `lat` | Median latitude of these cases, degrees (WGS 84) | float | `37.86671586568432` |
| `spread_m` | Largest distance from a case point to the median point, in metres, rounded to 0.1 m (haversine formula, Earth radius 6,371,008.8 m). 0 for a key with one case. | float | `149.1` |
| `Sector` | Beat sector of the median point, 1 to 14. Blank unless `sector_status` is `assigned`. | int | `6` |
| `sector_status` | `assigned`, `outside`, or `ambiguous` (see Rules) | str | `assigned` |

## Rules

- Address key: upper case, no spaces at the ends, and one space for each
  run of white space. For an intersection, the street names are sorted, so
  `PARKER ST & MILVIA ST` and `MILVIA ST & PARKER ST` give the key
  `MILVIA ST & PARKER ST`. Empty pieces left by a stray `&` are dropped. A
  blank address has no key.
- Sector of a point: the `Sector` of the beat polygon that contains it.
  `outside` means no polygon contains the point. `ambiguous` means the edge
  test finds the point on a polygon edge, or the point is inside two
  polygons. The edge test runs matplotlib `Path.contains_points` on each
  ring with radius +1e-10 and with radius -1e-10; the point is on the edge
  when the two answers differ. `missing` means the longitude or latitude is
  missing; the lookup has no such row.
- Status of a call (`bpdtools.sectors.attach_address_sectors`):

  | `sector_status` | Meaning | `Sector` |
  |---|---|---|
  | `assigned` | The key is in the table and its point is in one beat. | 1 to 14 |
  | `outside` | The key's point is outside every beat. | `<NA>` |
  | `ambiguous` | The key's point is on a beat edge or in two beats. | `<NA>` |
  | `no_point` | The key is in the table without a point (no such row now). | `<NA>` |
  | `unmatched` | The key is not in the table. | `<NA>` |
  | `blank_address` | The address is blank or missing. | `<NA>` |

- Sector of a crime case (`bpdtools.sectors.assign_case_sectors`): a case
  with a valid own point gets the sector of that point, also when the point
  is `outside` or `ambiguous`. Only a case without a point uses the table.
  `sector_source` records which location decided `sector_status`:

  | `sector_source` | Meaning | `sector_status` |
  |---|---|---|
  | `own_point` | The case has a valid point. | `assigned`, `outside`, `ambiguous` |
  | `address` | No point; the key has a point in the table. | `assigned`, `outside`, `ambiguous` |
  | `none` | No point, and no point for the key. | `no_point`, `unmatched`, `blank_address` |

## Counts that define the data

Of the 110,615 raw cases, the script leaves out 4,338: 2,187 with a blank
address (they are also the cases with the no-point code) and 2,151 whose
placeholder point was removed. No point is outside the box. The table is
built from 106,277 cases with a local date from 2016 to 2026 (one case has
no occurred time).

Rows by `sector_status`: 2,882 `assigned`, 30 `outside`, and 1 `ambiguous`
(`MILVIA ST & PARKER ST`). 1,153 keys are intersections, and 287 keys have
one case.

## Match rates

Calls for Service of `data/processed/calls_2021_2025.csv.gz`, 2021-2025,
with `attach_address_sectors`. The call groups are the exact labels in
`bpdtools/config.py`.

| Group | Calls | `assigned` | `unmatched` | `outside` | `ambiguous` |
|---|---:|---:|---:|---:|---:|
| All | 307,628 | 303,887 (98.78%) | 2,210 | 1,500 | 31 |
| Noise | 12,693 | 12,429 (97.92%) | 42 | 222 | 0 |
| Battery | 5,395 | 5,359 (99.33%) | 13 | 23 | 0 |
| Reckless driving | 2,549 | 2,472 (96.98%) | 60 | 16 | 1 |

No call is `no_point` or `blank_address`.

Assault cases of `data/processed/crime_cases_2021_2025.csv.gz`, 2021-2025
(3,567 cases), with `assign_case_sectors`:

| `sector_source` | `sector_status` | Cases |
|---|---|---:|
| `own_point` | `assigned` | 3,368 |
| `own_point` | `outside` | 21 |
| `own_point` | `ambiguous` | 5 |
| `address` | `assigned` | 114 |
| `none` | `unmatched` | 16 |
| `none` | `blank_address` | 43 |

In total, 3,482 assault cases have a sector.

## Limitations

- Spread: 33 keys have a `spread_m` over 300 m, and 6 over 1 km. One median
  point stands for all cases of a key, also when they lie far apart. Of the
  307,628 calls in 2021-2025, 27,969 (9.09%) are at these 33 keys.
- Headquarters placeholder: `2100 MARTIN LUTHER KING JR WAY` has 1,864
  cases, a spread of 3,265.3 m, and the headquarters point as its median
  point. The placeholder rule matches this address exactly, so cases with
  another spelling of the address lose their correct point.
- Keys outside the map: 30 keys have a median point outside every beat
  polygon, for example `2700 BANCROFT WAY` and `1600 SOLANO AVE`. Calls at
  these keys get no sector.
- Unmatched calls: the table only has addresses with a crime case. Of the
  2,210 `unmatched` calls, 1,335 are at a two-street intersection after
  normalization, and 455 end in `, BERKELEY` (for example
  `1600 5TH ST, BERKELEY`), which the key keeps.
- One map for every year: the beat map of 2026-11-22 is applied to cases
  from 2016 to 2026 and to calls from 2021 to 2025. Older beat boundaries
  were not checked.
- Edge test: the matplotlib test with radius +1e-10 and -1e-10 is not an
  exact distance to the edge. It can label a point within a few
  micrometres of an edge either way: `assigned` or `ambiguous`.
- `n_cases`, `lon`, and `lat` use cases from all years, including 2026. A
  new download can move a median point and change a sector.

## How to use

Read the table with `dtype={"block_key": str}`. Give calls the sector of
their address with `bpdtools.sectors.attach_address_sectors`, and give
crime cases the sector of their own point, or of their address when they
have no point, with `bpdtools.sectors.assign_case_sectors`. `Sector` is
pandas Int64 and is `<NA>` unless `sector_status` is `assigned`.

## How to rebuild

From the repository root, after `make env` has created the conda
environment:

```bash
make data
```

`make data` runs `python scripts/prepare_address_sectors.py` after the
Calls for Service and crime scripts. It needs the internet. To rebuild the
table from a raw crime file that is already in `data/downloads/`, run only
`python scripts/prepare_address_sectors.py`. A new download has new cases,
so the table and its SHA-256 can differ from the values above.
