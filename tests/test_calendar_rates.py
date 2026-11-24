"""Small examples exercise coverage, sector assignment, and zero denominators."""

import pandas as pd

from bpdtools.calendar_rates import period_rates


def test_coverage_and_campus_definitions():
    """Count true zero days, exclude unverified days, and move sector 4 in sensitivity."""
    dates = pd.date_range("2024-12-19", periods=5)
    calendar = pd.DataFrame({"date": dates, "semester": [1, 1, 0, 0, 0],
                             "winter_break": [0, 0, 1, 1, 1]})
    events = pd.DataFrame({"date": dates[[0, 0, 0, 2, 4]], "Sector": [6, 4, None, 6, 7]})
    primary, audit = period_rates(events, calendar, dates[:4], [6, 7])
    broader, _ = period_rates(events, calendar, dates[:4], [1, 4, 6, 7])
    assert primary.loc[("near", "semester"), "daily_rate"] == 0.5
    assert primary.loc[("near", "winter_break"), "semester_to_break_ratio"] == 1
    assert broader.loc[("near", "semester"), "semester_to_break_ratio"] == 2
    assert pd.isna(primary.loc[("other", "semester"), "semester_to_break_ratio"])
    assert audit.index.name == "period"
    assert audit.loc["semester", "unassigned_share"] == 1 / 3
