"""Download the BPD crime cases layer with coordinates to data/downloads/.

The source is the ArcGIS layer cases_latlon of the Berkeley PD Transparency
Hub. It has one row per case and statute. The script saves every attribute
field and every value as the layer returns it.

Run it from the repository root with `python scripts/download_crime_cases.py`.
"""

import csv
import json
import time
import urllib.parse

from bpdtools.download import (
    RETRY_ERRORS,
    open_url,
    partial_file,
    read_all_pages,
    with_retries,
)
from bpdtools.files import CSV_ENCODING, file_sha256
from bpdtools.paths import repo_path

# Query endpoint of the cases_latlon layer.
LAYER_URL = (
    "https://services7.arcgis.com/vIHhVXjE1ToSg0Fz/arcgis/rest/services/"
    "cases_latlon/FeatureServer/0/query"
)

# Query condition that selects every record of the layer.
ALL_RECORDS = "1=1"

# The layer returns at most 1000 records per request (its maxRecordCount).
PAGE_SIZE = 1000

# Seconds to wait between two pages, so that the server is not flooded.
PAGE_PAUSE_SECONDS = 0.5

# Errors after which another query can succeed: the shared network errors,
# an answer that is not valid JSON (often a cut-off reply), and an answer
# cut inside a multi-byte character, which cannot be decoded as text.
LAYER_RETRY_ERRORS = (*RETRY_ERRORS, json.JSONDecodeError, UnicodeDecodeError)

# Name of the unique row ID field of the layer.
ID_FIELD = "ObjectId"


def read_answer(url):
    """Send one query to the layer and decode its JSON answer.

    Parameters
    ----------
    url : str
        Full query URL with its parameters.

    Returns
    -------
    dict
        The decoded JSON answer.

    Raises
    ------
    urllib.error.URLError
        If the server cannot be reached or returns an HTTP error.
    http.client.HTTPException
        If the answer ends early.
    json.JSONDecodeError
        If the answer is not valid JSON.
    UnicodeDecodeError
        If the answer is cut inside a multi-byte character.
    """
    # Read the whole answer, then decode it. json.loads finds the text
    # encoding of the bytes by itself.
    with open_url(url) as response:
        return json.loads(response.read())


def fetch_json(params):
    """Query the layer, with retries, and return the decoded JSON answer.

    Parameters
    ----------
    params : dict of str to str
        Query parameters, for example ``{"where": "1=1", "f": "json"}``.

    Returns
    -------
    dict
        The JSON answer of the layer.

    Raises
    ------
    RuntimeError
        If every try fails, or if the answer holds an ArcGIS error object.
    urllib.error.HTTPError
        If the layer answers with a client error status other than 408 or
        429, such as 404. This error is not retried.
    """
    # Build the request URL and try the query a few times.
    url = LAYER_URL + "?" + urllib.parse.urlencode(params)
    answer = with_retries(
        lambda: read_answer(url), LAYER_URL, retry_on=LAYER_RETRY_ERRORS
    )
    # ArcGIS reports a failed query with HTTP 200 and an "error" object, so
    # a successful request is not enough. Such an error is not retried.
    if "error" in answer:
        raise RuntimeError(
            f"The layer returned an error: {answer['error']}. Check the query "
            "parameters in this script, or try again later."
        )
    return answer


def fetch_count():
    """Ask the layer how many records it holds.

    Returns
    -------
    int
        Number of records for the query that selects every record.

    Raises
    ------
    RuntimeError
        If the request fails or the answer has no count.
    urllib.error.HTTPError
        If the layer answers with a client error status other than 408 or
        429, such as 404.
    """
    # Ask for the count of all records only, without the records.
    answer = fetch_json({"where": ALL_RECORDS, "returnCountOnly": "true", "f": "json"})
    # Stop if the answer has no count, because the download is checked
    # against it.
    if "count" not in answer:
        raise RuntimeError(
            f"The count query gave no count: {answer}. Run the script again later."
        )
    return int(answer["count"])


def fetch_page(offset):
    """Read one page of records, ordered by ObjectId, and print its size.

    Every page but the first starts after a short pause, so that the
    server is not flooded.

    Parameters
    ----------
    offset : int
        Number of records to skip before the page starts.

    Returns
    -------
    field_names : list of str
        Attribute field names in layer order.
    page_records : list of dict
        One dict of attribute values per record, as the layer returns them.

    Raises
    ------
    RuntimeError
        If the request fails.
    urllib.error.HTTPError
        If the layer answers with a client error status other than 408 or
        429, such as 404.
    """
    # Short pause before every page but the first.
    if offset > 0:
        time.sleep(PAGE_PAUSE_SECONDS)
    # Ask for all attribute fields of one page, without the map geometry,
    # in a fixed ObjectId order so that the pages do not overlap.
    answer = fetch_json(
        {
            "where": ALL_RECORDS,
            "outFields": "*",
            "returnGeometry": "false",
            "orderByFields": ID_FIELD,
            "resultOffset": str(offset),
            "resultRecordCount": str(PAGE_SIZE),
            "f": "json",
        }
    )
    # Take the field names in layer order and the values of each record.
    field_names = [field["name"] for field in answer["fields"]]
    page_records = [feature["attributes"] for feature in answer["features"]]
    print(f"Read {len(page_records):,} records at offset {offset:,}")
    return field_names, page_records


def main():
    """Download the cases_latlon layer and print its rows, cases, and SHA-256.

    Returns
    -------
    None
        The function writes the raw CSV to data/downloads/.

    Raises
    ------
    RuntimeError
        If a request fails after every try, if the layer reports no records,
        or if the layer changed during the download.
    urllib.error.HTTPError
        If the layer answers with a client error status other than 408 or
        429, such as 404.
    OSError
        If the file in data/downloads/ cannot be written.
    """
    # The raw file goes to data/downloads/, which git ignores.
    target = repo_path("data", "downloads", "crime_cases.csv")
    # Ask for the record count first, so that the download can be checked.
    expected_count = fetch_count()
    print(f"The layer reports {expected_count:,} records")
    # Read every page, then write the file only after the checks of
    # read_all_pages passed: the same fields, no repeated ObjectId, and the
    # reported number of records.
    field_names, downloaded_records = read_all_pages(
        fetch_page, expected_count, PAGE_SIZE, ID_FIELD
    )
    # Write through a temporary file, so that a failed write never leaves a
    # half-written file at the target.
    with partial_file(target) as partial:
        with open(partial, "w", newline="", encoding=CSV_ENCODING) as output:
            writer = csv.writer(output, lineterminator="\n")
            writer.writerow(field_names)
            # Keep each value as returned: Occurred_Datetime stays an integer
            # of epoch milliseconds in UTC, and None becomes an empty cell.
            for attributes in downloaded_records:
                writer.writerow(
                    [
                        "" if attributes[name] is None else attributes[name]
                        for name in field_names
                    ]
                )
    # Print the rows, the distinct cases, and the checksum, with the path
    # relative to the repository root.
    n_cases = len({attributes["Case_Number"] for attributes in downloaded_records})
    print(f"Wrote {target.relative_to(repo_path())}")
    print(f"Rows: {len(downloaded_records):,}")
    print(f"Distinct Case_Number values: {n_cases:,}")
    print(f"SHA-256: {file_sha256(target)}")


if __name__ == "__main__":
    main()
