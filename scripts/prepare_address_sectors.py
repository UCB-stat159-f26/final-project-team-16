"""Build the lookup table from block address to police beat sector.

Reads the raw crime cases CSV in data/downloads/ (all years) and the beat
polygons data/boundaries/police_beats.geojson. Writes the lookup table, one
row per address key, as a CSV to data/processed/. Run this script from the
repository root with `python scripts/prepare_address_sectors.py`.
"""

from bpdtools.crime import (
    CASE_COLUMNS,
    clear_placeholder_points,
    one_row_per_case,
    read_raw_cases,
)
from bpdtools.files import file_sha256
from bpdtools.paths import repo_path
from bpdtools.sectors import build_lookup, load_sector_features


def main():
    """Build the address to sector lookup in data/processed/ and print counts.

    Returns
    -------
    None
        The function writes the output file and prints case and row counts.

    Raises
    ------
    FileNotFoundError
        If the raw crime download or the beats file is missing.
    ValueError
        If a column is missing, a map point is not a number, the statute
        rows of a case disagree, or the beats file is not valid.
    """
    # Read the raw download: one row per case and statute, all years. The
    # reader also turns the no-point code into a missing lat and lon.
    rows = read_raw_cases(
        repo_path("data", "downloads", "crime_cases.csv"),
        ["Case_Number", *CASE_COLUMNS],
    )
    print(f"Raw rows: {len(rows):,}, cases: {rows['Case_Number'].nunique():,}")

    # Deduplication: keep the first row of each Case_Number, so that each
    # case counts once. The function stops if the rows of a case disagree.
    cases = one_row_per_case(rows)
    # Remove the headquarters point from cases at another address, because
    # for them it is a placeholder, not the place of the case.
    cases = clear_placeholder_points(cases)

    # One row per address key, with its median point and sector. Cases
    # without a key, without a point, or outside the box are left out.
    lookup = build_lookup(cases, load_sector_features())

    # Write the table with LF line ends and no index; create the folder
    # when it does not exist yet.
    output = repo_path("data", "processed", "address_sectors.csv")
    output.parent.mkdir(parents=True, exist_ok=True)
    lookup.to_csv(output, index=False, lineterminator="\n")

    # Print the counts and the checksum of the result.
    print(f"Address keys: {len(lookup):,} from {lookup['n_cases'].sum():,} cases")
    print(f"Cases left out: {len(cases) - lookup['n_cases'].sum():,}")
    print(lookup["sector_status"].value_counts().to_string())
    print(f"Wrote {output.relative_to(repo_path())}")
    print(f"SHA-256: {file_sha256(output)}")


if __name__ == "__main__":
    main()
