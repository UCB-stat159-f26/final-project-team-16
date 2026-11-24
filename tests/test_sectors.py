"""Tests for bpdtools.sectors."""

import json

import pandas as pd
import pytest

from bpdtools.sectors import load_sector_features, normalize_block_address


def test_normalize_block_address_collapses_spaces_and_upper_cases():
    """Check that extra spaces go and the letters become upper case."""
    # Raw forms with spaces at the ends and doubled spaces or a tab inside.
    addresses = pd.Series(["  2400  telegraph Ave ", "1900\toxford ST"])
    result = normalize_block_address(addresses)
    assert result.tolist() == ["2400 TELEGRAPH AVE", "1900 OXFORD ST"]


def test_normalize_block_address_sorts_the_streets_of_an_intersection():
    """Check that both street orders give one key and a stray "&" is dropped."""
    # The same corner in two orders, one without spaces around "&", and an
    # address that ends with a stray "&".
    addresses = pd.Series(
        [
            "PARKER ST & MILVIA ST",
            "milvia st&parker st",
            "2400 TELEGRAPH AVE &",
        ]
    )
    result = normalize_block_address(addresses)
    assert result.tolist() == [
        "MILVIA ST & PARKER ST",
        "MILVIA ST & PARKER ST",
        "2400 TELEGRAPH AVE",
    ]


def test_normalize_block_address_keeps_blank_and_missing_values_missing():
    """Check that empty, all-space, "&"-only, and missing addresses give NaN."""
    # A custom index, which the result must keep.
    addresses = pd.Series(
        ["", "   ", " & ", None, "1900 oxford st"], index=[7, 8, 9, 10, 11]
    )
    result = normalize_block_address(addresses)
    assert result.index.tolist() == [7, 8, 9, 10, 11]
    assert result.isna().tolist() == [True, True, True, True, False]
    assert result.loc[11] == "1900 OXFORD ST"


def test_normalize_block_address_rejects_numbers():
    """Check that a number in place of an address raises a TypeError."""
    # A table read without dtype=str can hold numbers.
    with pytest.raises(TypeError, match="dtype=str"):
        normalize_block_address(pd.Series(["1900 OXFORD ST", 2400]))


def square(left, bottom, size=1.0, clockwise=False):
    """Build a closed square ring of (x, y) vertices.

    Parameters
    ----------
    left : float
        x value of the left side of the square.
    bottom : float
        y value of the bottom side of the square.
    size : float, default 1.0
        Length of each side.
    clockwise : bool, default False
        If True, list the vertices in clockwise order.

    Returns
    -------
    list of list of float
        Five vertices; the last one repeats the first, as in GeoJSON.
    """
    # Counter-clockwise corners, then the first corner again to close it.
    corners = [
        [left, bottom],
        [left + size, bottom],
        [left + size, bottom + size],
        [left, bottom + size],
    ]
    if clockwise:
        corners = corners[::-1]
    return [*corners, corners[0]]


def polygon_feature(sector_label, *rings):
    """Build a GeoJSON Polygon feature for one sector.

    Parameters
    ----------
    sector_label : str
        Value of the Sector property.
    *rings : list of list of float
        The shell ring, then any hole rings.

    Returns
    -------
    dict
        A GeoJSON feature with a Polygon geometry.
    """
    # Same structure as the features of police_beats.geojson.
    return {
        "type": "Feature",
        "properties": {"Sector": sector_label},
        "geometry": {"type": "Polygon", "coordinates": list(rings)},
    }


def two_squares():
    """Build two unit squares side by side: sector "1" left, "2" right.

    Returns
    -------
    list of dict
        Two features that share the edge x = 1 for 0 <= y <= 1.
    """
    # Sector 1 covers 0..1 and sector 2 covers 1..2 on the x axis.
    return [polygon_feature("1", square(0, 0)), polygon_feature("2", square(1, 0))]


def write_geojson(folder, features):
    """Write features as a GeoJSON FeatureCollection file.

    Parameters
    ----------
    folder : pathlib.Path
        Folder for the file, for example the tmp_path of a test.
    features : list of dict
        The features to write.

    Returns
    -------
    pathlib.Path
        Path of the new file beats.geojson.
    """
    # Same top-level structure as police_beats.geojson.
    geojson_path = folder / "beats.geojson"
    geojson_path.write_text(
        json.dumps({"type": "FeatureCollection", "features": features})
    )
    return geojson_path


def test_load_sector_features_reads_the_features(tmp_path):
    """Check that a file with two beats gives back both features."""
    # Write the two test squares, then read them back.
    geojson_path = write_geojson(tmp_path, two_squares())
    features = load_sector_features(geojson_path)
    assert [beat["properties"]["Sector"] for beat in features] == ["1", "2"]


def test_load_sector_features_rejects_a_point_geometry(tmp_path):
    """Check that a beat stored as a Point raises a ValueError."""
    # One feature whose geometry is a Point, not a polygon.
    point_beat = {
        "type": "Feature",
        "properties": {"Sector": "1"},
        "geometry": {"type": "Point", "coordinates": [0.5, 0.5]},
    }
    geojson_path = write_geojson(tmp_path, [point_beat])
    with pytest.raises(ValueError, match="Polygon or a MultiPolygon"):
        load_sector_features(geojson_path)


def test_load_sector_features_rejects_a_feature_without_sector(tmp_path):
    """Check that a beat without a Sector property raises a ValueError."""
    # A square whose properties have no Sector.
    unlabeled_beat = polygon_feature("1", square(0, 0))
    unlabeled_beat["properties"] = {"OBJECTID": 1}
    geojson_path = write_geojson(tmp_path, [unlabeled_beat])
    with pytest.raises(ValueError, match="no Sector property"):
        load_sector_features(geojson_path)


def test_load_sector_features_rejects_a_missing_file(tmp_path):
    """Check that a path without a file raises a FileNotFoundError."""
    # The folder is empty, so the file does not exist.
    with pytest.raises(FileNotFoundError, match="Beats file not found"):
        load_sector_features(tmp_path / "beats.geojson")
