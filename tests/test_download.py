"""Tests for bpdtools.download, without the network."""

import http.client
import io
import urllib.error

import pytest

from bpdtools.download import (
    TIMEOUT_SECONDS,
    USER_AGENT,
    ServerMessageError,
    check_first_line,
    open_url,
    partial_file,
    with_retries,
)

# Header of a small CSV for the header tests.
HEADER = "id,name"

# Address in the HTTP errors of the retry tests.
TEST_URL = "https://example.org/data.csv"


def make_stub_opener(body, seen_requests):
    """Make a stub for urllib.request.urlopen that records each request.

    Parameters
    ----------
    body : bytes
        Bytes that each response returns.
    seen_requests : list
        Empty list; each call appends a (request, timeout) pair to it.

    Returns
    -------
    callable
        A function with the call form of urlopen that returns an
        io.BytesIO response.
    """

    def stub_opener(request, timeout):
        """Record the request and return the body as a file-like response.

        Parameters
        ----------
        request : urllib.request.Request
            The request that open_url built.
        timeout : float
            The time-out in seconds that open_url passed.

        Returns
        -------
        io.BytesIO
            A response that holds `body`.
        """
        # Keep the request so that the test can read its header.
        seen_requests.append((request, timeout))
        return io.BytesIO(body)

    return stub_opener


def make_http_error(status):
    """Make the error that urlopen raises for an HTTP error status.

    Parameters
    ----------
    status : int
        HTTP status code, for example 404 or 503.

    Returns
    -------
    urllib.error.HTTPError
        An error for TEST_URL with this status and an empty body.
    """
    # An empty in-memory body stands in for the reply of the server.
    return urllib.error.HTTPError(TEST_URL, status, "stub reply", None, io.BytesIO())


def make_failing_action(errors, result):
    """Make a download step that raises the given errors, then succeeds.

    Parameters
    ----------
    errors : list of Exception
        Errors to raise on the first calls, in order.
    result : object
        Value to return once all errors are raised.

    Returns
    -------
    callable
        A function without arguments. Its `calls` attribute is a list that
        gets one entry per call.
    """
    remaining = list(errors)

    def action():
        """Raise the next error, or return the result when none is left.

        Returns
        -------
        object
            `result`, once every error was raised.

        Raises
        ------
        Exception
            The next error of `errors`, while one is left.
        """
        # Count the call, then fail while errors remain.
        action.calls.append(1)
        if remaining:
            raise remaining.pop(0)
        return result

    action.calls = []
    return action


def test_check_first_line_accepts_the_header_with_bom_and_crlf():
    """Check that a byte order mark and a CRLF line end are accepted."""
    # The function returns None and raises nothing.
    assert check_first_line(b"\xef\xbb\xbf" + HEADER.encode() + b"\r\n", HEADER) is None


def test_check_first_line_marks_a_json_reply_for_retry():
    """Check that a JSON status message raises a ServerMessageError."""
    # ArcGIS can send such a message while it prepares the file.
    with pytest.raises(ServerMessageError, match="message instead of the CSV"):
        check_first_line(b'{"status": "processing"}\n', HEADER)


def test_check_first_line_rejects_a_changed_header_without_retry():
    """Check that a changed header raises a ValueError, not a retry error."""
    # A renamed column is not a temporary problem.
    with pytest.raises(ValueError, match="changed the columns") as caught:
        check_first_line(b"id,full_name\n", HEADER)
    assert not isinstance(caught.value, ServerMessageError)


def test_open_url_sends_the_client_name_and_time_out():
    """Check the User-Agent header and the time-out given to the opener."""
    # The stub returns the body and keeps the request.
    seen_requests = []
    opener = make_stub_opener(b"id,name\n", seen_requests)
    with open_url("https://example.org/data.csv", opener=opener) as response:
        assert response.read() == b"id,name\n"
    request, timeout = seen_requests[0]
    assert request.get_header("User-agent") == USER_AGENT
    assert timeout == TIMEOUT_SECONDS


def test_partial_file_replaces_the_target_after_a_full_write(tmp_path):
    """Check that a finished write replaces the target and leaves no part file."""
    # An old file is in place before the new download.
    target = tmp_path / "data.csv"
    target.write_text("old\n")
    with partial_file(target) as partial:
        partial.write_text("new\n")
    assert target.read_text() == "new\n"
    assert [path.name for path in tmp_path.iterdir()] == ["data.csv"]


def test_partial_file_keeps_the_target_and_removes_the_part_file(tmp_path):
    """Check that an error keeps the old target and removes the part file."""
    # The write fails after half the file is written.
    target = tmp_path / "data.csv"
    target.write_text("old\n")
    with pytest.raises(ServerMessageError):
        with partial_file(target) as partial:
            partial.write_text("half")
            raise ServerMessageError("stub failure")
    assert target.read_text() == "old\n"
    assert [path.name for path in tmp_path.iterdir()] == ["data.csv"]


def test_with_retries_waits_longer_after_each_failure():
    """Check that two failures give waits of 10 and 20 seconds, then a result."""
    # A network error, then a server message, then success.
    action = make_failing_action(
        [urllib.error.URLError("no route"), ServerMessageError("busy")], "done"
    )
    pauses = []
    assert with_retries(action, "test source", sleep=pauses.append) == "done"
    assert pauses == [10, 20]
    assert len(action.calls) == 3


def test_with_retries_gives_up_after_the_last_try():
    """Check that four failures raise a RuntimeError after three waits."""
    # Every try fails with a time-out.
    action = make_failing_action([TimeoutError("slow")] * 4, "never")
    pauses = []
    with pytest.raises(RuntimeError, match="test source after 4 tries"):
        with_retries(action, "test source", sleep=pauses.append)
    assert pauses == [10, 20, 40]


def test_with_retries_does_not_retry_a_value_error():
    """Check that a ValueError, such as a changed header, stops at once."""
    # The first try fails with an error that another try cannot fix.
    action = make_failing_action([ValueError("changed header")], "never")
    pauses = []
    with pytest.raises(ValueError, match="changed header"):
        with_retries(action, "test source", sleep=pauses.append)
    assert len(action.calls) == 1
    assert pauses == []


def test_with_retries_retries_a_reply_that_ends_early():
    """Check that an IncompleteRead is retried and the next try succeeds."""
    # The connection closes before the whole file has arrived.
    action = make_failing_action([http.client.IncompleteRead(b"id,na")], "done")
    pauses = []
    assert with_retries(action, "test source", sleep=pauses.append) == "done"
    assert pauses == [10]
    assert len(action.calls) == 2


def test_with_retries_does_not_retry_a_404():
    """Check that an HTTP 404 error stops at once without a wait."""
    # A missing file will not appear on another try.
    action = make_failing_action([make_http_error(404)], "never")
    pauses = []
    with pytest.raises(urllib.error.HTTPError) as caught:
        with_retries(action, "test source", sleep=pauses.append)
    assert caught.value.code == 404
    assert len(action.calls) == 1
    assert pauses == []


def test_with_retries_retries_a_503():
    """Check that an HTTP 503 server error is retried after a wait."""
    # The server is busy for one try, then sends the data.
    action = make_failing_action([make_http_error(503)], "done")
    pauses = []
    assert with_retries(action, "test source", sleep=pauses.append) == "done"
    assert pauses == [10]
    assert len(action.calls) == 2


@pytest.mark.parametrize("status", [408, 429])
def test_with_retries_retries_a_408_or_a_429(status):
    """Check that an HTTP 408 or 429 client error is retried after a wait."""
    # A time-out or a rate limit for one try, then the server sends the data.
    action = make_failing_action([make_http_error(status)], "done")
    pauses = []
    assert with_retries(action, "test source", sleep=pauses.append) == "done"
    assert pauses == [10]
    assert len(action.calls) == 2
