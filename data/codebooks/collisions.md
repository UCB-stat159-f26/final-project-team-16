# Collisions

[Collisions](../processed/collisions.csv) contains one row per recorded collision, including undated collisions. The [preparation script](../../scripts/prepare_collisions.py) preserves all 16,639 records in the November 22, 2026 snapshot and adds the primary collision factor (PCF) classification. Missing counts below refer to empty CSV fields.

| Field | Type | Meaning and values | Missing |
|---|---|---|---|
| `ObjectId` | Integer | Unique source record identifier. | 0 |
| `DateTime` | Timestamp | Source UTC date and time, written M/D/YYYY with a 12-hour clock and no printed offset. | 103 |
| `Date` | Date | Berkeley local date, YYYY-MM-DD. Use for calendar matching. | 101 |
| `Time` | Time | Local time, HH:MM:SS in America/Los_Angeles. | 101 |
| `Month` | Integer | Local calendar month, 1–12. | 101 |
| `Year` | Integer | Local calendar year, 2007–2026 in this snapshot, with gaps. | 101 |
| `Day of Week` | Integer | Local weekday, Monday = 0 through Sunday = 6. | 101 |
| `Hour` | Integer | Local hour on the 24-hour clock. Only 1–23 appear in this snapshot. | 101 |
| `Accident Location` | Text | Reported street or intersection, with source spelling and abbreviations. | 0 |
| `PCF Description` | Text | Detailed recorded primary factor, often a vehicle-code citation and description. | 0 |
| `PCF Category` | Text | Broad source grouping, such as Speed Laws or Right of Way. | 0 |
| `Involved Objects` | Text | Counts and types of involved parties or objects, such as “1 Bicycle, 1 Car”. | 0 |
| `Party at Fault` | Category | Recorded type of party at fault: Driver, Bicyclist, Pedestrian, Other or Object. | 0 |
| `Suspected Serious Injury` | Integer | Number of suspected serious injuries, 0–3 observed. | 0 |
| `Suspected Minor Injury` | Integer | Number of suspected minor injuries, 0–6 observed. | 0 |
| `Suspected Possible Injury` | Integer | Number of suspected possible injuries, 0–4 observed. | 0 |
| `Injury Severity` | Category | Source collision classification: No Injury, Possible Injury, Minor Injury, Serious Injury, Fatal or Unspecified Injury. | 0 |
| `x` | Decimal | Easting in Web Mercator metres. | 1 |
| `y` | Decimal | Northing in Web Mercator metres. The same row lacks both coordinates. | 1 |
| `alcohol_pcf_status` | Category | Detailed PCF text classification: `explicit_alcohol`, `drug_only_label`, `unclear` or `other_pcf`. A4 counts only explicit alcohol or BAC wording (957 records). | 0 |

See the [PCF mapping](../mappings/collision_pcf.csv) for each description and its rationale. For hourly comparisons, the [data README](../README.md) documents unusual reporting before 06:00 and the restricted-hours check.
