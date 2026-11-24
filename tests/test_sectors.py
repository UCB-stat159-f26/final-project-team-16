"""Tests for bpdtools.sectors."""

import io
import json

import numpy as np
import pandas as pd
import pytest

from bpdtools.sectors import (
    EARTH_RADIUS_M,
    LOOKUP_COLUMNS,
    assign_case_sectors,
    assign_sectors,
    attach_address_sectors,
    build_lookup,
    haversine_m,
    load_sector_features,
    normalize_block_address,
)


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


def test_assign_sectors_labels_inside_and_outside_points():
    """Check that a point in a square gets its sector and a far point does not."""
    # (0.5, 0.5) is in sector 1, (1.5, 0.5) in sector 2, (5, 5) in neither.
    labels = assign_sectors([0.5, 1.5, 5.0], [0.5, 0.5, 5.0], two_squares())
    assert labels.tolist() == ["1", "2", "outside"]


def test_assign_sectors_marks_exact_edge_points_ambiguous():
    """Check that points on a shared edge and on an outer edge are ambiguous."""
    # (1, 0.5) is on the edge between the squares; (0, 0.5) is on the outer
    # edge of sector 1 only.
    labels = assign_sectors([1.0, 0.0], [0.5, 0.5], two_squares())
    assert labels.tolist() == ["ambiguous", "ambiguous"]


def test_assign_sectors_finds_edges_of_clockwise_rings():
    """Check that the edge test does not depend on the ring direction."""
    # The same square as sector 1, with its vertices in clockwise order.
    features = [polygon_feature("1", square(0, 0, clockwise=True))]
    labels = assign_sectors([0.5, 1.0], [0.5, 0.5], features)
    assert labels.tolist() == ["1", "ambiguous"]


def test_assign_sectors_marks_missing_points():
    """Check that a missing or infinite coordinate gives the label "missing"."""
    # One point without a longitude, one with an infinite latitude.
    labels = assign_sectors([np.nan, 0.5], [0.5, np.inf], two_squares())
    assert labels.tolist() == ["missing", "missing"]


def test_assign_sectors_uses_every_polygon_of_a_multipolygon():
    """Check that a point in the second polygon of a MultiPolygon gets its sector."""
    # Sector 3 has two separate squares; the second one starts at x = 3.
    split_beat = {
        "type": "Feature",
        "properties": {"Sector": 3},
        "geometry": {
            "type": "MultiPolygon",
            "coordinates": [[square(0, 0)], [square(3, 0)]],
        },
    }
    labels = assign_sectors([0.5, 3.5, 2.0], [0.5, 0.5, 0.5], [split_beat])
    assert labels.tolist() == ["3", "3", "outside"]


def test_assign_sectors_leaves_out_points_in_holes_and_overlaps():
    """Check that a hole is outside and a point in two polygons is ambiguous."""
    # Sector 1 is a 4 by 4 square with a hole from 1 to 2; sector 2 overlaps
    # sector 1 on the square from 3 to 4.
    features = [
        polygon_feature("1", square(0, 0, size=4), square(1, 1)),
        polygon_feature("2", square(3, 3)),
    ]
    labels = assign_sectors([1.5, 0.5, 3.5], [1.5, 0.5, 3.5], features)
    assert labels.tolist() == ["outside", "1", "ambiguous"]


def test_assign_sectors_rejects_lon_and_lat_of_different_length():
    """Check that two longitudes and one latitude raise a ValueError."""
    # Each point needs one longitude and one latitude.
    with pytest.raises(ValueError, match="one longitude and one latitude"):
        assign_sectors([0.5, 1.5], [0.5], two_squares())


def test_haversine_m_gives_zero_for_the_same_point():
    """Check that a point and itself are 0 m apart."""
    # One pair of equal points in Berkeley.
    distance = haversine_m([-122.26], [37.87], [-122.26], [37.87])
    assert distance.tolist() == [0.0]


def test_haversine_m_measures_one_degree_of_latitude():
    """Check that one degree north is 1/360 of the Earth's circumference."""
    # Along a meridian, the distance is the radius times the angle.
    distance = haversine_m([-122.0, -122.0], [37.0, 0.0], [-122.0, -122.0], [38.0, 1.0])
    expected = EARTH_RADIUS_M * np.pi / 180
    assert distance == pytest.approx([expected, expected])


def make_lookup_cases():
    """Build crime cases that test each rule of build_lookup.

    Returns
    -------
    pandas.DataFrame
        Columns Block_Address, lat, and lon as text, one row per case, on the
        two test squares: three cases of A ST in sector 1, two cases of one
        intersection in two street orders in sector 2, one case of C ST
        outside both squares, and cases that the rules leave out.
    """
    # The last three cases have no point, a point outside the box, or no
    # address, so the lookup does not use them.
    return pd.DataFrame(
        {
            "Block_Address": [
                "A ST",
                "a st",
                " A ST",
                "B ST & A ST",
                "A ST & B ST",
                "C ST",
                "D ST",
                "E ST",
                None,
            ],
            "lat": ["0.5", "0.5", "0.5", "0.5", "0.5", "1.5", None, "10", "0.5"],
            "lon": ["0.2", "0.4", "0.9", "1.5", "1.7", "2.5", None, "10", "0.5"],
        }
    )


def test_build_lookup_takes_the_median_point_of_each_key():
    """Check the keys, counts, median points, sectors, and statuses."""
    # The box from -1 to 2 (lat) and -1 to 3 (lon) leaves out E ST only.
    lookup = build_lookup(make_lookup_cases(), two_squares(), box=(-1, 2, -1, 3))
    assert list(lookup.columns) == list(LOOKUP_COLUMNS)
    assert lookup["block_key"].tolist() == ["A ST", "A ST & B ST", "C ST"]
    assert lookup["n_cases"].tolist() == [3, 2, 1]
    assert lookup["lon"].tolist() == pytest.approx([0.4, 1.6, 2.5])
    assert lookup["Sector"].astype("string").tolist() == ["1", "2", pd.NA]
    assert lookup["sector_status"].tolist() == ["assigned", "assigned", "outside"]


def test_build_lookup_gives_the_largest_distance_as_spread():
    """Check that spread_m is the farthest case from the median, or 0."""
    # A ST: the farthest case is at lon 0.9, the median at lon 0.4. The
    # intersection: both cases are 0.1 degrees from the median at lon 1.6.
    lookup = build_lookup(make_lookup_cases(), two_squares(), box=(-1, 2, -1, 3))
    farthest = haversine_m([0.9, 1.7], [0.5, 0.5], [0.4, 1.6], [0.5, 0.5])
    expected = [*farthest.round(1).tolist(), 0.0]
    assert lookup["spread_m"].tolist() == expected


def test_build_lookup_rejects_cases_without_block_address():
    """Check that a table without Block_Address raises a KeyError."""
    # The calls table spells the column "Block Address".
    calls = pd.DataFrame({"Block Address": ["A ST"], "lat": ["0.5"], "lon": ["0.5"]})
    with pytest.raises(KeyError, match="Block_Address"):
        build_lookup(calls, two_squares())


def make_lookup():
    """Build a small lookup table with one row for each lookup status.

    Returns
    -------
    pandas.DataFrame
        Columns block_key, Sector, and sector_status, as in
        data/processed/address_sectors.csv.
    """
    # Only the assigned rows have a sector. "missing" is a row without a
    # map point.
    return pd.DataFrame(
        {
            "block_key": ["A ST", "B ST", "C ST", "D ST", "A ST & B ST"],
            "Sector": pd.array([2, None, None, None, 1], dtype="Int64"),
            "sector_status": [
                "assigned",
                "outside",
                "ambiguous",
                "missing",
                "assigned",
            ],
        }
    )


def test_attach_address_sectors_gives_each_status():
    """Check the six statuses, the Int64 Sector, and the kept index."""
    # One call for each status, and one intersection written in the other
    # street order; the index is the incident number.
    calls = pd.DataFrame(
        {
            "Block Address": [
                " a  st",
                "B ST",
                "c st",
                "D ST",
                "E ST",
                "  ",
                None,
                "B ST & A ST",
            ]
        },
        index=pd.Index(
            [f"2024-0000000{position}" for position in range(8)], name="Incident Number"
        ),
    )
    result = attach_address_sectors(calls, make_lookup())
    assert result["sector_status"].tolist() == [
        "assigned",
        "outside",
        "ambiguous",
        "no_point",
        "unmatched",
        "blank_address",
        "blank_address",
        "assigned",
    ]
    assert str(result["Sector"].dtype) == "Int64"
    assert result["Sector"].iloc[0] == 2
    assert result["Sector"].iloc[1:7].isna().all()
    assert result["Sector"].iloc[7] == 1
    assert result.index.equals(calls.index)
    # The input table is not changed.
    assert list(calls.columns) == ["Block Address"]


def test_attach_address_sectors_reads_a_lookup_from_csv():
    """Check that a lookup read from CSV text gives Sector 6, not 6.0."""
    # A plain read_csv gives Sector as float64 with NaN for the blank cell.
    text = "block_key,Sector,sector_status\nA ST,6,assigned\nB ST,,outside\n"
    lookup = pd.read_csv(io.StringIO(text))
    crime_cases = pd.DataFrame({"Block_Address": ["A ST", "B ST"]})
    result = attach_address_sectors(crime_cases, lookup, address_column="Block_Address")
    assert result["Sector"].astype("string").tolist() == ["6", pd.NA]


def test_attach_address_sectors_rejects_repeated_lookup_keys():
    """Check that a block_key that occurs twice in the lookup raises."""
    # Two rows for the same key would match one call twice.
    lookup = pd.concat([make_lookup(), make_lookup().iloc[[0]]])
    calls = pd.DataFrame({"Block Address": ["A ST"]})
    with pytest.raises(ValueError, match="repeated block_key"):
        attach_address_sectors(calls, lookup)


def test_attach_address_sectors_rejects_a_missing_address_column():
    """Check that the wrong address column name raises a KeyError."""
    # The crime table spells the column Block_Address.
    crime_cases = pd.DataFrame({"Block_Address": ["A ST"]})
    with pytest.raises(KeyError, match="address_column"):
        attach_address_sectors(crime_cases, make_lookup())


def make_crime_cases():
    """Build six crime cases that cover each sector source and status.

    Returns
    -------
    pandas.DataFrame
        Columns Block_Address, lat, and lon as text, as in the crime cases
        table, with the case numbers as the index.
    """
    # Cases 1 and 2 have their own point (in sector 1, and outside every
    # beat). Cases 3 to 6 have no point: their address is assigned in the
    # lookup, outside in the lookup, not in the lookup, or blank.
    return pd.DataFrame(
        {
            "Block_Address": ["A ST", "A ST", "A ST", "B ST", "Z ST", None],
            "lat": ["0.5", "5.0", None, None, None, None],
            "lon": ["0.5", "5.0", None, None, None, None],
        },
        index=pd.Index(
            [f"2024-0000000{position}" for position in range(1, 7)], name="Case_Number"
        ),
    )


def test_assign_case_sectors_takes_point_then_address_then_none():
    """Check the source, status, and Sector of each of the six cases."""
    # Sector 1 is the left square; the lookup puts A ST in sector 2.
    crime_cases = make_crime_cases()
    result = assign_case_sectors(crime_cases, two_squares(), make_lookup())
    assert result["sector_source"].tolist() == [
        "own_point",
        "own_point",
        "address",
        "address",
        "none",
        "none",
    ]
    assert result["sector_status"].tolist() == [
        "assigned",
        "outside",
        "assigned",
        "outside",
        "unmatched",
        "blank_address",
    ]
    # The own point wins over the address: case 1 is in sector 1, not 2,
    # and case 2 does not fall back to the address.
    assert result["Sector"].astype("string").tolist() == [
        "1",
        pd.NA,
        "2",
        pd.NA,
        pd.NA,
        pd.NA,
    ]


def test_assign_case_sectors_keeps_the_index_and_the_input():
    """Check the Int64 Sector, the kept index, and the unchanged input."""
    # The function must return a copy and leave the input table as it is.
    crime_cases = make_crime_cases()
    result = assign_case_sectors(crime_cases, two_squares(), make_lookup())
    assert str(result["Sector"].dtype) == "Int64"
    assert result.index.equals(crime_cases.index)
    assert list(crime_cases.columns) == ["Block_Address", "lat", "lon"]


def test_assign_case_sectors_rejects_a_point_that_is_not_a_number():
    """Check that text in lat raises a ValueError that names lat and lon."""
    # "unknown" cannot be read as a latitude.
    crime_cases = pd.DataFrame(
        {"Block_Address": ["A ST"], "lat": ["unknown"], "lon": ["0.5"]}
    )
    with pytest.raises(ValueError, match="lat and lon must be numbers"):
        assign_case_sectors(crime_cases, two_squares(), make_lookup())
