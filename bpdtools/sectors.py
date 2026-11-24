"""Make block address keys that match across tables.

normalize_block_address turns block addresses into keys that match across
tables.
"""


def address_key(address):
    """Make the match key of one block address.

    Parameters
    ----------
    address : str
        One block address or intersection, as written in the source.

    Returns
    -------
    str or None
        The address in upper case with single spaces. For an intersection,
        the street names are sorted and joined by " & ". None when the
        address holds no street name.
    """
    # Upper case; split() also drops the spaces at both ends and treats each
    # run of white space as one break.
    text = " ".join(address.upper().split())
    # Split an intersection at each "&". Drop the empty pieces that a stray
    # "&" leaves, as in "2400 TELEGRAPH AVE &".
    names = [piece.strip() for piece in text.split("&") if piece.strip()]
    # A blank address has no name, so it has no key.
    if not names:
        return None
    # Sort the street names, so that "A ST & B ST" and "B ST & A ST" give
    # the same key. An address without "&" has one name and stays as it is.
    return " & ".join(sorted(names))


def normalize_block_address(addresses):
    """Turn block addresses into keys that match across tables.

    The key is the address in upper case, with the spaces at both ends
    removed and each run of white space replaced by one space. For an
    intersection ("A ST & B ST"), the street names are sorted, so that
    "A ST & B ST" and "B ST & A ST" give the same key. Empty pieces left by a
    stray "&" are dropped.

    Parameters
    ----------
    addresses : pandas.Series
        Block addresses as text. Missing values are allowed.

    Returns
    -------
    pandas.Series
        The keys as text, with the index of `addresses`. A missing address,
        or one that holds only white space or "&", gives a missing key.

    Raises
    ------
    TypeError
        If a value that is not missing is not text. Read the table with
        dtype=str to keep the addresses as text.
    """
    # Only text can be normalized; a number here means the table was read
    # without dtype=str.
    present = addresses.dropna()
    not_text = present[~present.apply(isinstance, args=(str,))]
    if not not_text.empty:
        raise TypeError(
            f"{len(not_text)} block addresses are not text, for example "
            f"{not_text.iloc[0]!r}. Read the table with dtype=str."
        )
    # Make the key of each address; a missing address stays missing.
    return addresses.map(address_key, na_action="ignore").astype("str")
