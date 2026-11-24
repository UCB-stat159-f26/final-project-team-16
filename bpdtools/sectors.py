"""Make block address keys and read the police beat polygons.

normalize_block_address turns block addresses into keys that match across
tables.
load_sector_features reads the beat polygons of
data/boundaries/police_beats.geojson.
"""

import json
import os
import pathlib

from bpdtools.paths import repo_path

# GeoJSON geometry types that a beat feature can have.
POLYGON_TYPES = ("Polygon", "MultiPolygon")


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


def load_sector_features(path=None):
    """Read the police beat polygons from a GeoJSON file.

    Parameters
    ----------
    path : str or pathlib.Path, optional
        Path of a GeoJSON FeatureCollection. The default is
        data/boundaries/police_beats.geojson in the repository.

    Returns
    -------
    list of dict
        The GeoJSON features, one per beat, in file order.

    Raises
    ------
    FileNotFoundError
        If the file does not exist.
    ValueError
        If the file has no "features" list, or if a feature is not a Polygon
        or MultiPolygon, or has no Sector property.
    """
    # Default: the beats file of the repository.
    if path is None:
        path = repo_path("data", "boundaries", "police_beats.geojson")
    path = pathlib.Path(path)
    # Show the path relative to the repository root in error messages.
    shown_path = os.path.relpath(path, repo_path())
    # Stop with a clear message when the file is not there.
    if not path.is_file():
        raise FileNotFoundError(
            f"Beats file not found: {shown_path}. Pass the path of the police "
            "beats GeoJSON file, or restore data/boundaries/police_beats.geojson."
        )
    # Read the FeatureCollection and take its list of features. json.loads
    # finds the text encoding of the bytes by itself.
    collection = json.loads(path.read_bytes())
    features = collection.get("features") if isinstance(collection, dict) else None
    if not isinstance(features, list):
        raise ValueError(
            f"{shown_path} has no 'features' list. Pass a GeoJSON FeatureCollection."
        )
    # Check every beat, so that a bad file fails here and not later.
    for position, beat in enumerate(features):
        geometry_type = (beat.get("geometry") or {}).get("type")
        if geometry_type not in POLYGON_TYPES:
            raise ValueError(
                f"Feature {position} of {shown_path} has geometry type "
                f"{geometry_type!r}. Each beat must be a Polygon or a MultiPolygon."
            )
        sector_label = (beat.get("properties") or {}).get("Sector")
        if sector_label is None or str(sector_label).strip() == "":
            raise ValueError(
                f"Feature {position} of {shown_path} has no Sector property. "
                "Add the sector number of the beat to its properties."
            )
    return features
