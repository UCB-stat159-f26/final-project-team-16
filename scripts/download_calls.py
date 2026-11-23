"""Download the raw Berkeley PD Calls for Service CSV into data/downloads/.

The raw file is about 58 MB and changes every day, so git ignores it. Run
this script from the repository root with `python scripts/download_calls.py`.
"""

import csv

from bpdtools.download import (
    DOWNLOAD_ENCODING,
    check_first_line,
    open_url,
    partial_file,
    with_retries,
)
from bpdtools.files import CHUNK_BYTES, file_sha256
from bpdtools.paths import repo_path

# Berkeley PD Calls for Service, 2019 - Current, as a CSV file.
CALLS_URL = (
    "https://www.arcgis.com/sharing/rest/content/items/"
    "272dfb0d5c5144679368fb2f97422a35/data"
)

# First line of a real Calls for Service CSV. The first column has no name,
# because it is a row index that the publisher saved with the data.
EXPECTED_HEADER = (
    ",Incident Number,CreateDatetime,Call Type,Source,Progress,Priority,"
    "Dispositions,Block Address,City,ZIP Code,NonBerkeley Address"
)

# Number of header lines at the start of the CSV.
HEADER_ROWS = 1


def save_calls(target):
    """Download the Calls for Service CSV once and check its first line.

    Parameters
    ----------
    target : pathlib.Path
        File to write. The old file is replaced only after the header check.

    Returns
    -------
    None
        The function writes `target` and returns nothing.

    Raises
    ------
    urllib.error.URLError
        If the server cannot be reached or returns an HTTP error.
    http.client.HTTPException
        If the reply ends before the whole file has arrived.
    bpdtools.download.ServerMessageError
        If the server sent a status message instead of the CSV.
    ValueError
        If the first line is not the expected header.
    OSError
        If `target` cannot be written.
    """
    # Write to a temporary file, so that a failed try never replaces a good
    # file; the temporary file is removed after an error.
    with partial_file(target) as partial:
        # Stream the reply to disk in blocks.
        with open_url(CALLS_URL) as response, open(partial, "wb") as output:
            while chunk := response.read(CHUNK_BYTES):
                output.write(chunk)
        # Reject a JSON status message, an HTML page, or changed columns.
        with open(partial, "rb") as written:
            check_first_line(written.readline(), EXPECTED_HEADER)


def main():
    """Download the Calls for Service CSV and print its size, rows, and SHA-256.

    Returns
    -------
    None
        The function writes the raw CSV to data/downloads/.

    Raises
    ------
    RuntimeError
        If every download try fails with a network error, a server message,
        or a 408 or 429 status.
    urllib.error.HTTPError
        If the server answers with a client error status other than 408 or
        429, such as 404. This error is not retried.
    ValueError
        If the columns of the file changed. This error is not retried.
    OSError
        If the file in data/downloads/ cannot be written.
    """
    # Try the download a few times, with a pause, because the server can be
    # slow or send a status message before the file is ready.
    target = repo_path("data", "downloads", "calls_for_service.csv")
    with_retries(lambda: save_calls(target), CALLS_URL)

    # Count records with the csv module, which handles quoted line breaks.
    # The header record is not a data row, so it is not counted.
    with open(target, newline="", encoding=DOWNLOAD_ENCODING) as source:
        n_rows = sum(1 for _ in csv.reader(source)) - HEADER_ROWS
    # Print the facts of the new file, with its path relative to the root.
    print(f"Wrote {target.relative_to(repo_path())}")
    print(f"Size: {target.stat().st_size:,} bytes")
    print(f"Rows: {n_rows:,}")
    print(f"SHA-256: {file_sha256(target)}")


if __name__ == "__main__":
    main()
