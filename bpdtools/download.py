"""Shared settings and helpers for the scripts that download raw data."""

import contextlib
import http.client
import os
import time
import urllib.error
import urllib.request

# A generic client name, so that the request carries no personal data.
USER_AGENT = "stat159-course-project"

# How long to wait for the server before one try fails.
TIMEOUT_SECONDS = 120

# How often to try a download, and the wait before the first retry. The
# wait doubles after each failed try.
MAX_ATTEMPTS = 4
RETRY_PAUSE_SECONDS = 10

# Suffix of the temporary file that holds a download until it is complete.
PARTIAL_SUFFIX = ".part"

# How many characters of a wrong first line to show in an error message.
MAX_SHOWN_CHARACTERS = 200

# Text encoding of a downloaded CSV. "utf-8-sig" also removes a byte order
# mark at the start of the file, if there is one.
DOWNLOAD_ENCODING = "utf-8-sig"


class ServerMessageError(Exception):
    """The server sent a status message or an error page instead of the data.

    Another try can succeed, because the server often sends such a message
    while it prepares the file.
    """


# HTTP statuses from 400 to 499 mean a client error, for example 403
# Forbidden or 404 Not Found. Server errors (500 to 599) are retried.
CLIENT_ERROR_STATUSES = range(400, 500)

# The two client errors that are temporary: 408 Request Timeout and 429 Too
# Many Requests. A later try can succeed, so with_retries retries them with
# the usual pauses. For every other client error another try gets the same
# answer, so with_retries stops at once.
RETRIED_CLIENT_STATUSES = (408, 429)

# Errors after which another try can succeed: network errors (also a reply
# that ends early, such as http.client.IncompleteRead), HTTP server errors,
# time-outs, and a server message in place of the data. An HTTP error with
# a status in CLIENT_ERROR_STATUSES is a URLError too, but with_retries does
# not retry it unless the status is in RETRIED_CLIENT_STATUSES. A ValueError
# is not here, so a changed CSV header stops the download at once.
RETRY_ERRORS = (
    urllib.error.URLError,
    http.client.HTTPException,
    ConnectionError,
    TimeoutError,
    ServerMessageError,
)


def check_first_line(first_line, expected_header):
    """Check that the first line of a downloaded CSV is the expected header.

    Parameters
    ----------
    first_line : bytes
        The first line of the downloaded file, with or without its line end.
    expected_header : str
        The header line that the file must start with, without a line end.

    Returns
    -------
    None
        The function returns nothing when the header is correct.

    Raises
    ------
    ServerMessageError
        If the line starts like a JSON message or an HTML page. Another try
        can succeed.
    ValueError
        If the line is another text, which means that the columns of the
        file changed. Another try cannot fix this.
    """
    # Remove a byte order mark and the line end (CRLF or LF).
    text = first_line.decode(DOWNLOAD_ENCODING, errors="replace").rstrip("\r\n")
    if text == expected_header:
        return
    shown_text = repr(text[:MAX_SHOWN_CHARACTERS])
    # A JSON status message or an HTML error page is a temporary reply.
    if text.lstrip().startswith(("{", "<")):
        raise ServerMessageError(
            f"The server sent a message instead of the CSV: {shown_text}. Wait "
            "a few minutes and run the download again."
        )
    # Any other first line means that the publisher changed the columns.
    raise ValueError(
        f"The first line of the download is {shown_text}, not the expected "
        "header. The publisher may have changed the columns; check the new "
        "columns and update the expected header in the download script."
    )


def open_url(url, opener=urllib.request.urlopen):
    """Open a URL with the project's client name and time-out.

    Parameters
    ----------
    url : str
        Address to open.
    opener : callable, default urllib.request.urlopen
        Function that takes a urllib.request.Request and a `timeout` keyword
        and returns a file-like response. Tests pass a stub here.

    Returns
    -------
    file-like object
        The response of `opener`. Use it in a `with` block and read it with
        its `read` method.

    Raises
    ------
    urllib.error.URLError
        If the server cannot be reached or returns an HTTP error.
    TimeoutError
        If the server does not answer within TIMEOUT_SECONDS.
    """
    # Send the generic client name with every request.
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    return opener(request, timeout=TIMEOUT_SECONDS)


@contextlib.contextmanager
def partial_file(target):
    """Give a temporary path that replaces `target` only after a full write.

    Write the new file to the yielded path inside a `with` block. When the
    block ends without an error, the file replaces `target` in one step.
    When the block raises, `target` stays as it was. In both cases no
    temporary file is left behind.

    Parameters
    ----------
    target : pathlib.Path
        Final path of the file. Missing parent folders are created.

    Yields
    ------
    pathlib.Path
        The temporary path, `target` with PARTIAL_SUFFIX added to its name.

    Raises
    ------
    OSError
        If the folder cannot be created or the file cannot be moved.
    """
    # Create the folder, then name the temporary file next to the target.
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + PARTIAL_SUFFIX)
    try:
        yield partial
        # The write finished, so the new file replaces the old one.
        os.replace(partial, target)
    finally:
        # Remove a half-written file after an error; after a successful
        # replace the temporary file no longer exists.
        partial.unlink(missing_ok=True)


def with_retries(action, source_name, retry_on=RETRY_ERRORS, sleep=time.sleep):
    """Call a download step again after a temporary error.

    Parameters
    ----------
    action : callable
        Function without arguments that does one try of the download step.
    source_name : str
        Name or URL of the source, for the messages.
    retry_on : tuple of type, default RETRY_ERRORS
        Errors after which another try follows. Any other error stops at
        once, and so does an HTTP error with a status in CLIENT_ERROR_STATUSES
        that is not in RETRIED_CLIENT_STATUSES.
    sleep : callable, default time.sleep
        Function that waits a number of seconds. Tests pass a stub here.

    Returns
    -------
    object
        The return value of the first successful call of `action`.

    Raises
    ------
    RuntimeError
        If all MAX_ATTEMPTS tries fail with an error of `retry_on`.
    urllib.error.HTTPError
        If the server answers with a status in CLIENT_ERROR_STATUSES other
        than 408 and 429 (RETRIED_CLIENT_STATUSES). This error is raised at
        the first such answer, without another try.
    """
    # Try the step up to MAX_ATTEMPTS times; return at the first success.
    last_error = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return action()
        except retry_on as error:
            # Threshold: a client error (status 400 to 499) other than 408 or
            # 429 will not change on another try, so stop at once. A server
            # error, 408, and 429 are retried.
            if (
                isinstance(error, urllib.error.HTTPError)
                and error.code in CLIENT_ERROR_STATUSES
                and error.code not in RETRIED_CLIENT_STATUSES
            ):
                raise
            last_error = error
            print(f"Try {attempt} of {MAX_ATTEMPTS} failed: {error}")
            # Wait longer after each failure, but only when another try
            # follows.
            if attempt < MAX_ATTEMPTS:
                sleep(RETRY_PAUSE_SECONDS * 2 ** (attempt - 1))
    raise RuntimeError(
        f"Could not read {source_name} after {MAX_ATTEMPTS} tries: {last_error}. "
        "Wait a few minutes, check the internet connection, and run the "
        "script again."
    ) from last_error


def read_all_pages(fetch_page, expected_count, records_per_page, unique_id_field):
    """Read a paged data source and check that the pages fit together.

    Parameters
    ----------
    fetch_page : callable
        Function that takes the offset of a page (int, the number of records
        to skip) and returns a pair (field_names, page_records): a list of
        field names in source order, and a list with one dict of values per
        record. Tests pass a stub here.
    expected_count : int
        Number of records that the source reported before the download.
    records_per_page : int
        Number of records per page. The offsets are 0, `records_per_page`,
        2 * `records_per_page`, and so on, while they are below
        `expected_count`.
    unique_id_field : str
        Name of the field that holds the unique ID of a record.

    Returns
    -------
    field_names : list of str
        Field names of the first page, in source order.
    downloaded_records : list of dict
        The records of all pages, in page order.

    Raises
    ------
    RuntimeError
        If `expected_count` is 0, because then there is no page to read.
        Also if the pages have different fields, if an ID repeats, or if
        the number of records differs from `expected_count`. Each of these
        last three means that the source changed during the download; run
        the download again. An error of `fetch_page` is passed on unchanged.
    """
    # Threshold: a source that reports no records has no page and no field
    # names, so stop with a clear message before any page is read.
    if expected_count == 0:
        raise RuntimeError(
            "The source reported no records, so there is nothing to download. "
            "Check that the query selects records and that the source address "
            "is right, then run the download again."
        )
    # Read the pages one after the other, `records_per_page` records each.
    field_names = None
    downloaded_records = []
    seen_ids = set()
    for offset in range(0, expected_count, records_per_page):
        page_fields, page_records = fetch_page(offset)
        # All pages must have the same fields in the same order.
        if field_names is None:
            field_names = page_fields
        elif page_fields != field_names:
            raise RuntimeError(
                f"The page at offset {offset} has other fields than the first "
                "page. Run the download again."
            )
        # Deduplication check: offset paging on a live source can repeat a
        # record when rows are added during the download, so stop on a
        # repeated ID instead of keeping the record twice.
        for attributes in page_records:
            if attributes[unique_id_field] in seen_ids:
                raise RuntimeError(
                    f"{unique_id_field} {attributes[unique_id_field]} appears "
                    "twice. The source changed during the download; run it "
                    "again."
                )
            seen_ids.add(attributes[unique_id_field])
        downloaded_records.extend(page_records)
    # A missing or extra record also means that the source changed.
    if len(downloaded_records) != expected_count:
        raise RuntimeError(
            f"Downloaded {len(downloaded_records):,} records, but the source "
            f"reported {expected_count:,}. Run the download again."
        )
    return field_names, downloaded_records
