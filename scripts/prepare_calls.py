"""Build the 2021-2025 Calls for Service table from the raw download.

Reads the raw CSV in data/downloads/ and writes the 2021-2025 table as a
gzip CSV to data/processed/. Run this script from the repository root with
`python scripts/prepare_calls.py`.
"""

import pandas as pd

from bpdtools.calls import N_EXAMPLES, local_dates, read_raw_calls
from bpdtools.config import (
    ANALYSIS_END,
    ANALYSIS_START,
    BATTERY_CALL_TYPES,
    DATE_FORMAT,
    NOISE_CALL_TYPES,
    RECKLESS_CALL_TYPES,
)
from bpdtools.files import write_gzip_csv
from bpdtools.paths import repo_path

# Columns of the output table, in order. "date" is the local date that this
# script adds; the others are source columns, kept as text.
OUTPUT_COLUMNS = [
    "Incident Number",
    "CreateDatetime",
    "date",
    "Call Type",
    "Source",
    "Block Address",
    "ZIP Code",
]

# Length of the date part at the start of a CreateDatetime value.
DATE_TEXT_LENGTH = len("2024-11-03")


def main():
    """Build the 2021-2025 table in data/processed/ and print what was left out.

    Returns
    -------
    None
        The function writes the output file and prints row counts.

    Raises
    ------
    FileNotFoundError
        If the raw download is missing.
    ValueError
        If a column is missing, a local date differs from the written date,
        an Incident Number is blank or repeated, or a Call Type label of the
        config groups does not occur.
    """
    # Read the raw download as text, with the columns that the output uses.
    raw = read_raw_calls(
        repo_path("data", "downloads", "calls_for_service.csv"),
        [column for column in OUTPUT_COLUMNS if column != "date"],
    )
    print(f"Raw rows: {len(raw):,}")

    # Time zone step: parse each offset and take the local date.
    raw["date"] = local_dates(raw["CreateDatetime"])
    # The source writes local time with its offset, so each local date must
    # equal the first 10 characters of the text. Blank values have no date.
    is_dated = raw["date"].notna()
    written = raw.loc[is_dated, "CreateDatetime"].str[:DATE_TEXT_LENGTH]
    computed = raw.loc[is_dated, "date"].dt.strftime(DATE_FORMAT)
    moved = written != computed
    if moved.any():
        examples = written[moved].head(N_EXAMPLES).tolist()
        raise ValueError(
            f"{int(moved.sum())} local dates differ from the written date, for "
            f"example {examples}. Check that CreateDatetime still holds local "
            "time with its UTC offset."
        )

    # Filter: keep dated rows inside the analysis window (inclusive dates).
    is_blank = raw["date"].isna()
    is_before = raw["date"] < pd.Timestamp(ANALYSIS_START)
    is_after = raw["date"] > pd.Timestamp(ANALYSIS_END)
    calls = raw[~is_blank & ~is_before & ~is_after].copy()
    print(f"Left out, blank CreateDatetime: {int(is_blank.sum()):,}")
    print(f"Left out, before {ANALYSIS_START}: {int(is_before.sum()):,}")
    print(f"Left out, after {ANALYSIS_END}: {int(is_after.sum()):,}")
    print(f"Kept rows: {len(calls):,}")

    # One row is one call, so no deduplication is needed. Stop if a key is
    # blank or repeated, because then a row would not be one call.
    numbers = calls["Incident Number"].str.strip()
    n_blank = int((numbers == "").sum())
    n_repeated = int(numbers.duplicated().sum())
    if n_blank or n_repeated:
        raise ValueError(
            f"Incident Number has {n_blank} blank and {n_repeated} repeated "
            "values. Inspect these rows in the raw file before building the table."
        )

    # Exact label match: stop if a label of the config groups has no row, so
    # that a renamed label cannot give a silent zero count.
    groups = {
        "noise": NOISE_CALL_TYPES,
        "battery": BATTERY_CALL_TYPES,
        "reckless": RECKLESS_CALL_TYPES,
    }
    present = set(calls["Call Type"])
    absent = [
        label
        for group_labels in groups.values()
        for label in group_labels
        if label not in present
    ]
    if absent:
        raise ValueError(
            f"Call Type labels {absent} do not occur in the table. Update the "
            "groups in bpdtools/config.py to the labels in the new file."
        )

    # Sort by the source time text, then by Incident Number for equal times.
    calls = calls.sort_values(["CreateDatetime", "Incident Number"], kind="stable")
    calls["date"] = calls["date"].dt.strftime(DATE_FORMAT)

    # Print the size of each Call Type group, matched by exact label.
    for group_name, group_labels in groups.items():
        n_group = int(calls["Call Type"].isin(group_labels).sum())
        print(f"{group_name} calls: {n_group:,}")

    # Write the kept columns and print the checksum of the result.
    output = repo_path("data", "processed", "calls_2021_2025.csv.gz")
    sha256 = write_gzip_csv(calls[OUTPUT_COLUMNS], output)
    print(f"Wrote {output.relative_to(repo_path())}")
    print(f"SHA-256: {sha256}")


if __name__ == "__main__":
    main()
