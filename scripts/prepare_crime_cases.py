"""Build the 2021-2025 crime cases table with one row per case.

Reads the raw crime cases CSV in data/downloads/ and writes the 2021-2025
table as a gzip CSV to data/processed/. Run this script from the repository
root with `python scripts/prepare_crime_cases.py`.
"""

import pandas as pd

from bpdtools.config import (
    ANALYSIS_END,
    ANALYSIS_START,
    ASSAULT_INCIDENT_TYPES,
    DATE_FORMAT,
)
from bpdtools.crime import (
    clear_placeholder_points,
    local_times_from_epoch,
    one_row_per_case,
    read_raw_cases,
)
from bpdtools.files import write_gzip_csv
from bpdtools.paths import repo_path

# Columns of the output table, in order. "date" is the local date that this
# script adds; the others are source columns.
OUTPUT_COLUMNS = [
    "Case_Number",
    "Occurred_Datetime",
    "date",
    "Incident_Type",
    "Block_Address",
    "ZIP_Code",
    "lat",
    "lon",
]

# Text format of the local time in the output.
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def main():
    """Build the 2021-2025 table in data/processed/ and print its counts.

    Returns
    -------
    None
        The function writes the output file and prints row and case counts.

    Raises
    ------
    FileNotFoundError
        If the raw download is missing.
    ValueError
        If a column is missing, an occurred time is not a number, a map
        point is not a number, or the statute rows of a case disagree.
    """
    # Read the raw download: one row per case and statute. The reader also
    # turns the no-point code into a missing lat and lon.
    rows = read_raw_cases(
        repo_path("data", "downloads", "crime_cases.csv"),
        [column for column in OUTPUT_COLUMNS if column != "date"],
    )
    print(f"Raw rows: {len(rows):,}, cases: {rows['Case_Number'].nunique():,}")
    print(f"Raw rows without a map point: {int(rows['lat'].isna().sum()):,}")

    # Time zone step: Occurred_Datetime is UTC epoch milliseconds, so convert
    # it to America/Los_Angeles local time with the daylight saving rules.
    local_times = local_times_from_epoch(rows["Occurred_Datetime"])
    print(f"Rows left out, blank occurred time: {int(local_times.isna().sum()):,}")

    # Filter: keep rows whose local date is inside the analysis window, both
    # ends included. Rows without a time have no date and are left out.
    occurred_dates = local_times.dt.normalize()
    in_window = occurred_dates.between(
        pd.Timestamp(ANALYSIS_START), pd.Timestamp(ANALYSIS_END)
    )
    rows = rows.loc[in_window].copy()
    # Store the local time as text without an offset, and the local date.
    rows["Occurred_Datetime"] = local_times[in_window].dt.strftime(TIME_FORMAT)
    rows["date"] = occurred_dates[in_window].dt.strftime(DATE_FORMAT)
    print(f"Rows in {ANALYSIS_START} to {ANALYSIS_END}: {len(rows):,}")

    # Deduplication: keep one row per Case_Number. The function stops if the
    # statute rows of a case disagree on time, type, address, or point.
    cases = one_row_per_case(rows)

    # Remove the headquarters point from cases at another address, because
    # for them it is a placeholder, not the place of the case.
    n_points_before = int(cases["lat"].notna().sum())
    cases = clear_placeholder_points(cases)
    n_cleared = n_points_before - int(cases["lat"].notna().sum())
    print(f"Cases whose placeholder point was cleared: {n_cleared:,}")

    # Sort by local time, then case number, for a stable row order.
    cases = cases.sort_values(["Occurred_Datetime", "Case_Number"], kind="stable")
    cases = cases[OUTPUT_COLUMNS].reset_index(drop=True)

    # Print the size of the assault group, matched by exact label.
    is_assault = cases["Incident_Type"].isin(ASSAULT_INCIDENT_TYPES)
    print(f"Cases: {len(cases):,}")
    print(f"Assault cases: {int(is_assault.sum()):,}")

    # Write the table and print the checksum of the result.
    output = repo_path("data", "processed", "crime_cases_2021_2025.csv.gz")
    sha256 = write_gzip_csv(cases, output)
    print(f"Wrote {output.relative_to(repo_path())}")
    print(f"SHA-256: {sha256}")


if __name__ == "__main__":
    main()
