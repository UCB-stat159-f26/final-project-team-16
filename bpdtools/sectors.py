"""Place block addresses, calls, and crime cases in police beat sectors.

normalize_block_address turns block addresses into keys that match across
tables.
load_sector_features reads the beat polygons of
data/boundaries/police_beats.geojson.
assign_sectors places map points in these polygons.
haversine_m measures the distance between two map points.
build_lookup gives each address key one map point and its sector.
attach_address_sectors gives each call the sector of its block address from
data/processed/address_sectors.csv.
assign_case_sectors gives each crime case the sector of its own map point,
or of its block address when the case has no point.
"""

import json
import os
import pathlib

import numpy as np
import pandas as pd
from matplotlib.path import Path as PolygonPath

from bpdtools.crime import lat_lon_numbers, require_columns
from bpdtools.paths import repo_path

# GeoJSON geometry types that a beat feature can have.
POLYGON_TYPES = ("Polygon", "MultiPolygon")

# Labels of assign_sectors for points that get no sector.
NO_SECTOR_LABELS = ("missing", "outside", "ambiguous")

# Radius in degrees of the edge test of assign_sectors. The test runs
# matplotlib's contains_points with +EDGE_RADIUS and with -EDGE_RADIUS; a
# point for which the two answers differ is on the edge of the ring.
EDGE_RADIUS = 1e-10

# Mean radius of the Earth in metres, for the haversine distance.
EARTH_RADIUS_M = 6_371_008.8

# Box around Berkeley in degrees, as (south lat, north lat, west lon, east
# lon), with the limits left out. A case point outside it is not a Berkeley
# location (a geocoding error), so it must not pull the address point away.
BERKELEY_BOX = (37.84, 37.91, -122.33, -122.22)

# Number of decimals of spread_m in the lookup table (0.1 m).
SPREAD_DECIMALS = 1

# Columns of the lookup table that build_lookup returns, in order.
LOOKUP_COLUMNS = (
    "block_key",
    "n_cases",
    "lon",
    "lat",
    "spread_m",
    "Sector",
    "sector_status",
)

# Columns of the crime cases that build_lookup and assign_case_sectors
# read.
CASE_LOCATION_COLUMNS = ("Block_Address", "lat", "lon")

# Values of sector_status in the lookup table: a label of assign_sectors for
# a point without a sector, or "assigned" when the point is in one sector.
LOOKUP_STATUSES = ("assigned", *NO_SECTOR_LABELS)

# Columns that attach_address_sectors adds to the events, and that the
# lookup table must have.
ADDRESS_SECTOR_COLUMNS = ("block_key", "Sector", "sector_status")

# Columns that assign_case_sectors adds to the crime cases.
CASE_SECTOR_COLUMNS = ("Sector", "sector_source", "sector_status")

# Statuses of attach_address_sectors for an address that has a map point in
# the lookup table.
ADDRESS_POINT_STATUSES = ("assigned", "outside", "ambiguous")


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


def assign_sectors(lon, lat, features):
    """Label each map point with the police beat sector that contains it.

    The edge test runs matplotlib's Path.contains_points on each polygon ring
    twice, with radius +1e-10 and with radius -1e-10 (EDGE_RADIUS). A point
    for which the two answers differ is on the edge. This is a test of the
    matplotlib function, not an exact distance to the edge.

    Parameters
    ----------
    lon : array-like of float
        Longitude of each point in degrees (EPSG:4326).
    lat : array-like of float
        Latitude of each point in degrees, in the same order as `lon`.
    features : list of dict
        GeoJSON beat features, for example from load_sector_features. Each
        has a Polygon or MultiPolygon geometry and a Sector property.

    Returns
    -------
    numpy.ndarray of object
        One str label per point: the Sector as text (for example "6"),
        "missing" if lon or lat is not a finite number, "outside" if no
        polygon contains the point, or "ambiguous" if the edge test finds
        the point on a polygon edge or the point is inside two polygons.

    Raises
    ------
    ValueError
        If `lon` and `lat` have different lengths, or if a feature is not a
        Polygon or MultiPolygon.
    """
    # Read the coordinates as float arrays; each point needs both.
    lon = np.asarray(lon, dtype=float)
    lat = np.asarray(lat, dtype=float)
    if lon.shape != lat.shape:
        raise ValueError(
            f"lon has {lon.size} values and lat has {lat.size}. Pass one "
            "longitude and one latitude for each point."
        )
    # Stack the coordinates as an N-by-2 array of (lon, lat) points.
    points = np.column_stack([lon, lat])
    # A point with a missing or infinite coordinate cannot be placed.
    valid = np.isfinite(points).all(axis=1)
    labels = np.full(len(points), "outside", dtype=object)
    labels[~valid] = "missing"
    # Test the points against each beat in turn, in the order of the file.
    for beat in features:
        sector_label = str(beat["properties"]["Sector"])
        geometry = beat["geometry"]
        # Treat a Polygon as a MultiPolygon with one polygon.
        polygons = geometry["coordinates"]
        if geometry["type"] == "Polygon":
            polygons = [polygons]
        elif geometry["type"] != "MultiPolygon":
            raise ValueError(
                f"Sector {sector_label} has geometry type {geometry['type']!r}. "
                "Each beat must be a Polygon or a MultiPolygon."
            )
        inside = np.zeros(len(points), dtype=bool)
        boundary = np.zeros(len(points), dtype=bool)
        for shell, *holes in polygons:
            # A point is in a polygon when it is inside the shell and not
            # inside any of its holes.
            in_polygon = np.ones(len(points), dtype=bool)
            for ring_index, ring in enumerate([shell, *holes]):
                ring_path = PolygonPath(ring)
                # Edge threshold: run contains_points with a tiny positive
                # and a tiny negative radius. The two answers differ only
                # near the edge, whatever the winding direction of the ring.
                grown = ring_path.contains_points(points, radius=EDGE_RADIUS)
                shrunk = ring_path.contains_points(points, radius=-EDGE_RADIUS)
                boundary |= grown ^ shrunk
                in_ring = grown & shrunk
                in_polygon &= in_ring if ring_index == 0 else ~in_ring
            inside |= in_polygon
        # A point on an edge, or a point that an earlier beat already
        # claimed, is ambiguous and gets no sector.
        ambiguous = boundary | (inside & (labels != "outside"))
        labels[inside & valid] = sector_label
        labels[ambiguous & valid] = "ambiguous"
    return labels


def haversine_m(start_lon, start_lat, end_lon, end_lat):
    """Compute the great-circle distance between pairs of points.

    Parameters
    ----------
    start_lon : array-like of float
        Longitude of the first point of each pair, in degrees.
    start_lat : array-like of float
        Latitude of the first point of each pair, in degrees.
    end_lon : array-like of float
        Longitude of the second point of each pair, in degrees.
    end_lat : array-like of float
        Latitude of the second point of each pair, in degrees.

    Returns
    -------
    numpy.ndarray of float
        Distance in metres between the two points of each pair, on a sphere
        with radius EARTH_RADIUS_M.
    """
    # Convert the degrees to radians.
    start_lon, start_lat, end_lon, end_lat = (
        np.radians(np.asarray(values, dtype=float))
        for values in (start_lon, start_lat, end_lon, end_lat)
    )
    # Haversine formula for the central angle between the two points.
    half_chord = (
        np.sin((end_lat - start_lat) / 2) ** 2
        + np.cos(start_lat) * np.cos(end_lat) * np.sin((end_lon - start_lon) / 2) ** 2
    )
    return 2 * EARTH_RADIUS_M * np.arcsin(np.sqrt(half_chord))


def build_lookup(cases, features, box=BERKELEY_BOX):
    """Give each block address key one map point and the sector of that point.

    The point of a key is the median longitude and the median latitude of
    its cases, so that a few far points move it less than a mean would.

    Parameters
    ----------
    cases : pandas.DataFrame
        One row per crime case, for example after one_row_per_case and
        clear_placeholder_points of bpdtools.crime. Must contain
        Block_Address, lat, and lon; lat and lon can be numbers or text.
    features : list of dict
        GeoJSON beat features from load_sector_features.
    box : tuple of float, default BERKELEY_BOX
        (south lat, north lat, west lon, east lon) in degrees. Only points
        strictly inside the box are used.

    Returns
    -------
    pandas.DataFrame
        The columns of LOOKUP_COLUMNS, one row per block_key, sorted by
        block_key. n_cases counts the cases used for the key. spread_m is
        the largest distance in metres from a case point to the median
        point, rounded to SPREAD_DECIMALS. Sector is pandas Int64 and is
        <NA> unless sector_status is "assigned"; otherwise sector_status is
        "outside" or "ambiguous".

    Raises
    ------
    KeyError
        If Block_Address, lat, or lon is missing.
    ValueError
        If a lat or lon value is not a number.
    TypeError
        If a Block_Address value is not text.
    """
    # Stop early with a clear message when a needed column is missing.
    require_columns(cases, CASE_LOCATION_COLUMNS, "crime cases")
    # Read the coordinates as numbers; a blank cell becomes NaN.
    latitudes, longitudes = lat_lon_numbers(cases, "crime cases")
    # Keep only the address key and the point of each case.
    points = pd.DataFrame(
        {
            "block_key": normalize_block_address(cases["Block_Address"]),
            "lon": longitudes,
            "lat": latitudes,
        }
    )
    # Filter: a case needs an address key and a point to place its address.
    has_key_and_point = (
        points["block_key"].notna() & points["lon"].notna() & points["lat"].notna()
    )
    # Threshold: keep only points strictly inside the box.
    south_lat, north_lat, west_lon, east_lon = box
    in_box = (
        points["lat"].gt(south_lat)
        & points["lat"].lt(north_lat)
        & points["lon"].gt(west_lon)
        & points["lon"].lt(east_lon)
    )
    points = points.loc[has_key_and_point & in_box]

    # One point per address: the median longitude and the median latitude
    # over its cases. Each case counts once.
    lookup = points.groupby("block_key", sort=True).agg(
        n_cases=("lon", "size"), lon=("lon", "median"), lat=("lat", "median")
    )
    # Spread: the largest distance from a case point to the median point of
    # its address, in metres (0 for an address with one case).
    median_points = lookup.loc[points["block_key"], ["lon", "lat"]].to_numpy()
    distance = haversine_m(
        points["lon"], points["lat"], median_points[:, 0], median_points[:, 1]
    )
    lookup["spread_m"] = (
        pd.Series(distance, index=points.index).groupby(points["block_key"]).max()
    ).round(SPREAD_DECIMALS)
    # The sector of the address is the sector of its median point.
    labels = pd.Series(
        assign_sectors(lookup["lon"], lookup["lat"], features), index=lookup.index
    )
    is_sector = ~labels.isin(NO_SECTOR_LABELS)
    lookup["Sector"] = pd.to_numeric(labels.where(is_sector)).astype("Int64")
    lookup["sector_status"] = labels.where(~is_sector, "assigned")
    return lookup.reset_index()[list(LOOKUP_COLUMNS)]


def attach_address_sectors(events, lookup, address_column="Block Address"):
    """Give each event the police beat sector of its block address.

    Parameters
    ----------
    events : pandas.DataFrame
        One row per call or case. Must contain `address_column`.
    lookup : pandas.DataFrame
        The table read from data/processed/address_sectors.csv, with the
        columns block_key, Sector, and sector_status and one row per
        block_key.
    address_column : str, default "Block Address"
        Name of the block address column of `events`. Use "Block_Address"
        for the crime cases table.

    Returns
    -------
    pandas.DataFrame
        A copy of `events`, with the same index, and three new columns:
        block_key (the normalized address), Sector (pandas Int64, <NA> unless
        the status is "assigned"), and sector_status. The status is
        "assigned", "outside", or "ambiguous" as in the lookup, "no_point"
        when the lookup has the address but no map point for it, "unmatched"
        when the address is not in the lookup, and "blank_address" when the
        address is blank or missing.

    Raises
    ------
    KeyError
        If `address_column` is not in `events`, or a lookup column is missing.
    ValueError
        If `events` already has one of the new columns, if a block_key of the
        lookup is blank or repeated, if a sector_status is unknown, or if
        Sector is filled for a row that is not "assigned" (or the reverse).
    TypeError
        If an address of `events` is not text.
    """
    # Check the columns of both tables.
    if address_column not in events.columns:
        raise KeyError(
            f"events has no column {address_column!r}. Pass the name of its "
            "block address column as address_column."
        )
    require_columns(lookup, ADDRESS_SECTOR_COLUMNS, "lookup")
    taken_columns = [
        column for column in ADDRESS_SECTOR_COLUMNS if column in events.columns
    ]
    if taken_columns:
        raise ValueError(
            f"events already has the columns {taken_columns}. Drop them before "
            "attaching sectors again."
        )
    # Deduplication check: each lookup key must be present and appear once,
    # so that every event matches at most one row.
    lookup_keys = lookup["block_key"]
    if lookup_keys.isna().any() or lookup_keys.duplicated().any():
        raise ValueError(
            "lookup has a blank or repeated block_key. Rebuild it with "
            "`python scripts/prepare_address_sectors.py`."
        )
    # Every status must be one of LOOKUP_STATUSES.
    lookup_status = lookup["sector_status"]
    unknown = sorted(set(lookup_status) - set(LOOKUP_STATUSES), key=str)
    if unknown:
        raise ValueError(
            f"lookup has unknown sector_status values {unknown}. Allowed values "
            f"are {list(LOOKUP_STATUSES)}."
        )
    # A CSV read gives Sector as float with NaN; store it as whole numbers
    # with <NA>.
    lookup_sector = pd.to_numeric(lookup["Sector"]).astype("Int64")
    if (lookup_sector.notna() != (lookup_status == "assigned")).any():
        raise ValueError(
            "lookup must have a Sector exactly on the rows whose sector_status "
            "is 'assigned'. Rebuild it with "
            "`python scripts/prepare_address_sectors.py`."
        )

    # Normalize the event addresses with the rule that built the lookup keys.
    result = events.copy()
    result["block_key"] = normalize_block_address(result[address_column])
    # Look up each key with map, which keeps the index and the row count.
    key_index = pd.Index(lookup_keys.astype("str"))
    sector_by_key = pd.Series(lookup_sector.array, index=key_index)
    status_by_key = pd.Series(lookup_status.astype("str").array, index=key_index)
    result["Sector"] = result["block_key"].map(sector_by_key).astype("Int64")
    event_status = result["block_key"].map(status_by_key)
    # A lookup row without a map point is reported as "no_point".
    event_status = event_status.replace({"missing": "no_point"})
    # An address that the lookup does not have is "unmatched", and a blank
    # address is "blank_address".
    event_status = event_status.mask(event_status.isna(), "unmatched")
    event_status = event_status.mask(result["block_key"].isna(), "blank_address")
    result["sector_status"] = event_status.astype("str")
    return result


def assign_case_sectors(cases, features, lookup):
    """Give each crime case the police beat sector of its point or address.

    A case with a valid map point gets the sector of its own point, even when
    that point is outside every beat. Only a case without a valid point (lat
    or lon missing) gets the sector of its block address from the lookup
    table, in the way of attach_address_sectors.

    Parameters
    ----------
    cases : pandas.DataFrame
        One row per crime case, for example the table read from
        data/processed/crime_cases_2021_2025.csv.gz. Must contain
        Block_Address, lat, and lon. lat and lon can be numbers or text.
    features : list of dict
        GeoJSON beat features from load_sector_features.
    lookup : pandas.DataFrame
        The table read from data/processed/address_sectors.csv.

    Returns
    -------
    pandas.DataFrame
        A copy of `cases`, with the same index, and three new columns.
        Sector is pandas Int64, <NA> unless sector_status is "assigned".
        sector_source is "own_point" when the case has a valid point; then
        sector_status is "assigned", "outside", or "ambiguous" for that
        point. sector_source is "address" when the case has no valid point
        and the lookup has a point for its address; then sector_status is
        "assigned", "outside", or "ambiguous" for the address point.
        sector_source is "none" when the case has neither; then
        sector_status is "no_point", "unmatched", or "blank_address", as in
        attach_address_sectors.

    Raises
    ------
    KeyError
        If Block_Address, lat, or lon is missing, or a lookup column is
        missing.
    ValueError
        If `cases` already has one of the new columns, if a lat or lon value
        is not a number, or if the lookup breaks a rule of
        attach_address_sectors.
    TypeError
        If a Block_Address value is not text.
    """
    # Stop early with a clear message when a needed column is missing.
    require_columns(cases, CASE_LOCATION_COLUMNS, "crime cases")
    taken_columns = [
        column for column in CASE_SECTOR_COLUMNS if column in cases.columns
    ]
    if taken_columns:
        raise ValueError(
            f"cases already has the columns {taken_columns}. Drop them before "
            "assigning sectors again."
        )
    # Read the coordinates as numbers; a blank cell becomes NaN.
    latitudes, longitudes = lat_lon_numbers(cases, "crime cases")

    # Place each case by its own point. A case without a valid point gets
    # the label "missing".
    point_labels = pd.Series(
        assign_sectors(longitudes, latitudes, features), index=cases.index
    )
    has_point = point_labels != "missing"
    is_sector = ~point_labels.isin(NO_SECTOR_LABELS)
    point_sector = pd.to_numeric(point_labels.where(is_sector)).astype("Int64")
    point_status = point_labels.where(~is_sector, "assigned")

    # Look up the address of every case. Only the cases without a valid
    # point use this result.
    by_address = attach_address_sectors(
        cases[["Block_Address"]], lookup, address_column="Block_Address"
    )

    # Fallback rule: keep the own point when there is one, else the address.
    result = cases.copy()
    result["Sector"] = point_sector.where(has_point, by_address["Sector"])
    # Source: the own point, the address point, or none when the address has
    # no point in the lookup (no_point, unmatched, or blank_address).
    has_address_point = by_address["sector_status"].isin(ADDRESS_POINT_STATUSES)
    sector_source = np.select(
        [has_point.to_numpy(), has_address_point.to_numpy()],
        ["own_point", "address"],
        default="none",
    )
    result["sector_source"] = pd.Series(sector_source, index=cases.index).astype("str")
    result["sector_status"] = point_status.where(
        has_point, by_address["sector_status"]
    ).astype("str")
    return result
