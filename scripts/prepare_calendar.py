"""Expand reviewed event windows to one row per local calendar date."""
import csv
from datetime import date, timedelta
from pathlib import Path


def daily_flags(windows):
    """Expand inclusive event windows to one record per calendar day.

    Parameters
    ----------
    windows : iterable of dict
        Rows with an event_type and ISO start_date and end_date strings.

    Yields
    ------
    dict
        An ISO date and a 0 or 1 flag for each event type.

    Raises
    ------
    ValueError
        If a date cannot be parsed, the input is empty, a window ends
        before it starts, or an event type uses the reserved name "date".
    """
    # Parse the source dates before comparing window boundaries.
    intervals = [(r["event_type"], date.fromisoformat(r["start_date"]),
                  date.fromisoformat(r["end_date"])) for r in windows]
    # Require at least one window and ordered endpoints.
    if not intervals or any(end < start for _, start, end in intervals):
        raise ValueError("Expected nonempty windows with start <= end")
    kinds = sorted({kind for kind, _, _ in intervals})
    # Reserve the date column for the calendar day.
    if "date" in kinds:
        raise ValueError("Event type date is reserved for the calendar date column")
    # Cover every day between the earliest start and latest end.
    day = min(start for _, start, _ in intervals)
    last = max(end for _, _, end in intervals)
    # Keep independent flags so overlapping events survive the expansion.
    while day <= last:
        active = {kind for kind, start, end in intervals if start <= day <= end}
        yield {"date": day.isoformat(), **{k: int(k in active) for k in kinds}}
        day += timedelta(days=1)


def main():
    """Take no arguments, write the daily calendar beside its source, and return None."""
    folder = Path(__file__).resolve().parents[1] / "data/calendar"
    # Read the source windows and expand them into daily records.
    with (folder / "event_windows.csv").open(newline="", encoding="utf-8") as src:
        rows = list(daily_flags(csv.DictReader(src)))
    # Write the date and event flags in the generated column order.
    with (folder / "daily_calendar.csv").open("w", newline="", encoding="utf-8") as dst:
        writer = csv.DictWriter(dst, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} days, {rows[0]['date']} through {rows[-1]['date']}")


if __name__ == "__main__":
    main()
