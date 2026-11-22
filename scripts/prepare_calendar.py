"""Expand reviewed event windows to one row per local calendar date."""
import csv
from datetime import date, timedelta
from pathlib import Path


def daily_flags(windows):
    """Yield date and integer indicator dictionaries from CSV window dictionaries.

    Include every day from the first window start to the last window end.
    Each event type has an independent flag, including both endpoints.
    """
    intervals = [(r["event_type"], date.fromisoformat(r["start_date"]),
                  date.fromisoformat(r["end_date"])) for r in windows]
    if not intervals or any(end < start for _, start, end in intervals):
        raise ValueError("Expected nonempty windows with start <= end")
    kinds = sorted({kind for kind, _, _ in intervals})
    day = min(start for _, start, _ in intervals)
    last = max(end for _, _, end in intervals)
    while day <= last:
        active = {kind for kind, start, end in intervals if start <= day <= end}
        yield {"date": day.isoformat(), **{k: int(k in active) for k in kinds}}
        day += timedelta(days=1)


def main():
    """Read event_windows.csv and write daily_calendar.csv beside it."""
    folder = Path(__file__).resolve().parents[1] / "data/calendar"
    with (folder / "event_windows.csv").open(newline="", encoding="utf-8") as src:
        rows = list(daily_flags(csv.DictReader(src)))
    with (folder / "daily_calendar.csv").open("w", newline="", encoding="utf-8") as dst:
        writer = csv.DictWriter(dst, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} days, {rows[0]['date']} through {rows[-1]['date']}")


if __name__ == "__main__":
    main()
