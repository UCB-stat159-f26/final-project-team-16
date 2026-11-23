"""Write data files that are the same byte for byte, and compute checksums."""

import gzip
import hashlib

# Read files in blocks of this many bytes, so that a large file is never
# held in memory at once.
CHUNK_BYTES = 1024 * 1024

# Fixed modification time in the gzip header. A real time would change the
# bytes of the file on every run.
GZIP_MTIME = 0

# Strongest gzip compression level.
GZIP_COMPRESS_LEVEL = 9

# Text encoding of the CSV inside the gzip file.
CSV_ENCODING = "utf-8"


def file_sha256(path):
    """Compute the SHA-256 checksum of a file.

    Parameters
    ----------
    path : pathlib.Path
        The file to hash.

    Returns
    -------
    str
        The SHA-256 checksum as a hexadecimal string of 64 characters.

    Raises
    ------
    FileNotFoundError
        If `path` does not exist.
    """
    # Hash the raw bytes block by block.
    digest = hashlib.sha256()
    with open(path, "rb") as source:
        while chunk := source.read(CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def write_gzip_csv(frame, path):
    """Write a table as a gzip CSV that is the same byte for byte on each run.

    Parameters
    ----------
    frame : pandas.DataFrame
        The table to write. Its index is not written.
    path : pathlib.Path
        Output file, normally ending in .csv.gz. Missing parent folders are
        created, and an existing file is overwritten.

    Returns
    -------
    str
        The SHA-256 checksum of the written file, as a hexadecimal string.
    """
    # LF line ends and no index give the same CSV text on every system.
    text = frame.to_csv(index=False, lineterminator="\n")
    # Create the output folder when it does not exist yet.
    path.parent.mkdir(parents=True, exist_ok=True)
    # A fixed time and an empty stored file name keep the gzip header the
    # same on every run and in every folder.
    with open(path, "wb") as output:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=output,
            mtime=GZIP_MTIME,
            compresslevel=GZIP_COMPRESS_LEVEL,
        ) as compressed:
            compressed.write(text.encode(CSV_ENCODING))
    return file_sha256(path)
