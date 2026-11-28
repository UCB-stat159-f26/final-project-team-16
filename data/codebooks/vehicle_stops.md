# Vehicle stops

[Vehicle stops](../processed/vehicle_stops.csv) contains one row per vehicular stop. The [preparation script](../../scripts/prepare_vehicle_stops.py) retained 7,603 person records from the November 22, 2026 snapshot and collapsed them to 7,431 distinct stops. A stop involving multiple people counts once. Missing counts below refer to empty CSV fields in that snapshot.

| Field | Type | Meaning and values | Missing |
|---|---|---|---|
| `LEA_Record_ID` | Text | Department stop identifier, unique in this file. Preserve its prefix and zeros. | 0 |
| `TypeOfStopDesc` | Text | Source stop classification. Every included row is `Vehicular Stop`. | 0 |
| `StopDate` | Date | Local stop date in MM/DD/YYYY format, January 1, 2024 through May 26, 2026. | 0 |
| `StopTime` | Time | Local start time in 24-hour HH:MM format. | 0 |
| `Latitude` | Decimal | Reported latitude in degrees. Use with longitude for beat assignment. | 46 |
| `Longitude` | Decimal | Reported longitude in degrees. The same 46 stops lack both coordinates. | 46 |

The dated records do not establish uninterrupted daily coverage. For the source and snapshot checksum, see the [data README](../README.md).
