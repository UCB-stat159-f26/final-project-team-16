# Fall 2024 academic and event calendar

The [source windows](../calendar/event_windows.csv) record 20 named intervals. The [daily calendar](../calendar/daily_calendar.csv) expands those intervals to one row per Berkeley local date, August 20, 2024 through January 13, 2025 inclusive. Neither file has empty fields in this snapshot.

## Source windows

| Field | Type | Meaning and values |
|---|---|---|
| `event_type` | Category | One of the 12 indicator names in the daily table below. Games share the same type. |
| `event_name` | Text | Human-readable event or period name, such as Cal vs. Stanford. |
| `start_date` | Date | First included local date in YYYY-MM-DD format. |
| `end_date` | Date | Last included local date in YYYY-MM-DD format. A one-day event has identical endpoints. |
| `source_url` | URL | Source used to verify the window. |
| `accessed_on` | Date | Date the source was consulted, YYYY-MM-DD. All entries show 2026-11-22. |

## Daily calendar

The date key uses YYYY-MM-DD. Every other field is an integer: 1 means a window of that type includes the date, and 0 means none does. Multiple indicators can be 1 on the same day. These flags describe the calendar; police reporting coverage is checked separately.

| Field | Meaning of the date or indicator |
|---|---|
| `date` | Unique local date. All 147 consecutive dates are present. |
| `finals` | Fall final examinations, December 16–20. |
| `formal_classes_end` | Registrar’s formal classes end date, December 6. |
| `halloween` | October 31. |
| `holiday` | Holiday window listed in the source table. |
| `home_football` | A Cal home football game, seven dates total. |
| `instruction_begins` | First day of fall instruction, August 28. |
| `last_instruction_day` | Registrar’s last day of instruction, December 13. |
| `move_in` | New-student move-in, August 20–21. |
| `non_instructional` | Designated non-instructional day before Thanksgiving. |
| `rrr` | Reading, Review, and Recitation Week, December 9–13. |
| `semester` | Fall semester, August 21 through December 20 (122 days, including weekends). |
| `winter_break` | Winter break, December 21 through January 13 (24 days). |

August 20 is a move-in day outside both A3 periods. August 21 belongs to both move-in and the semester.
