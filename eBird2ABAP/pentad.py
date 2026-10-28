"""
Pentad grid system utilities for SABAP (Southern African Bird Atlas Project).

A pentad is a 5-minute by 5-minute geographic grid cell used for bird atlas data collection.
This module provides functions for:
- Converting between lat/lng coordinates and pentad IDs
- Generating pentad polygons
- Creating pentad grids covering geographic areas
"""

import numpy as np
import geopandas as gpd
from shapely.geometry import box


# ============================================================================
# Core Pentad ID Conversions
# ============================================================================

def _grid_nw_corner(lat, lng):
    """Return signed north/west edges in integer five-minute grid units.

    Shared edges belong to the cell south/east of the edge:
    latitude (south, north], longitude [west, east). Snap only floating-point
    noise near exact grid lines (1e-10 grid units, about one micrometre).
    """
    lat_grid = np.asarray(lat, dtype=float) * 12
    lng_grid = np.asarray(lng, dtype=float) * 12
    lat_grid = np.where(np.isclose(lat_grid, np.rint(lat_grid), rtol=0, atol=1e-10), np.rint(lat_grid), lat_grid)
    lng_grid = np.where(np.isclose(lng_grid, np.rint(lng_grid), rtol=0, atol=1e-10), np.rint(lng_grid), lng_grid)
    return np.ceil(lat_grid).astype(int), np.floor(lng_grid).astype(int)


def latlng2pentad(lat, lng):
    """
    Convert latitude and longitude coordinates to pentad IDs.
    
    The ID encodes the northwest corner of a 5' x 5' cell, following the
    SABAP2 manual (section 2.2) and Brooks et al. (2022). Northern latitude
    uses the north edge; western longitude uses the west edge. Published
    website labels that disagree with this rule are not special-cased.
    On shared edges, assign south/east: (south, north] x [west, east).
    Format: XXYYcZZWW
    - XX: Latitude degrees
    - YY: Latitude minutes (00, 05, ..., 55)
    - c: Quadrant character ('_', 'a', 'b', 'c')
    - ZZ: Longitude degrees
    - WW: Longitude minutes (00, 05, ..., 55)
    
    Parameters:
    -----------
    lat : float or list-like
        Latitude(s) in decimal degrees.
    lng : float or list-like
        Longitude(s) in decimal degrees.
        
    Returns:
    --------
    list of str
        List of pentad IDs corresponding to the input coordinates.
    """
    # Convert inputs to numpy arrays for vectorized operations
    lat = np.asarray(lat)
    lng = np.asarray(lng)
    
    # Handle scalar inputs by wrapping them in 1D arrays
    if lat.ndim == 0 and lng.ndim == 0:
        lat = lat[np.newaxis]
        lng = lng[np.newaxis]
        
    # Input validation
    if lat.shape != lng.shape:
        raise ValueError("Latitude and longitude arrays must have the same shape.")
    if np.any(np.abs(lat) > 90):
        raise ValueError("Latitude values must be between -90 and 90 degrees.")
    if np.any(np.abs(lng) > 180):
        raise ValueError("Longitude values must be between -180 and 180 degrees.")
    
    north, west = _grid_nw_corner(lat, lng)
    lat_minutes = np.abs(north) * 5
    lng_minutes = np.abs(west) * 5
    quadrant = np.where(north > 0, np.where(west < 0, "b", "c"), np.where(west < 0, "a", "_"))
    return [
        f"{y // 60:02d}{y % 60:02d}{q}{x // 60:02d}{x % 60:02d}"
        for y, x, q in zip(lat_minutes, lng_minutes, quadrant)
    ]


# ============================================================================
# Helper Functions
# ============================================================================

def pentad2latlng(pentads):
    """
    Converts pentad IDs to their center latitude and longitude coordinates.
    
    The pentad ID represents the NW corner of the grid cell.
    The center is always 2.5 arcminutes south and 2.5 arcminutes east of
    the northwest corner. This is independent of hemisphere.
    
    Parameters:
    -----------
    pentads : str or list of str
        Pentad ID(s) in the format "XXYYcZZWW" (see latlng2pentad for details).
    
    Returns:
    --------
    tuple of lists
        (lat, lng) - Center coordinates of each pentad.
    
    Example:
    --------
    >>> pentads = ["2530_2750", "3435a2925"]
    >>> lat, lng = pentad2latlng(pentads)
    >>> print(lat)  # Approximately [-25.541667, -34.625]
    >>> print(lng)  # Approximately [27.875, -29.375]
    """
    # Accept a single pentad string or a list/array
    if isinstance(pentads, str):
        pentads = [pentads]
    pentads = np.array(pentads)

    # Input validation
    for i, p in enumerate(pentads):
        if not isinstance(p, str):
            raise TypeError(f"Element at index {i} is not a string: {p}")
        if len(p) != 9:
            raise ValueError(f"Element at index {i} is not 9 characters long: {p}")
        if not (p[0:4].isdigit() and p[5:9].isdigit()):
            raise ValueError(f"Element at index {i} has non-numeric degrees or minutes: {p}")
        if p[4] not in ["_", "a", "b", "c"]:
            raise ValueError(f"Element at index {i} has an invalid quadrant character '{p[4]}': {p}")

    # Extract components
    lat_deg = np.array([int(p[0:2]) for p in pentads])
    lat_min = np.array([int(p[2:4]) for p in pentads])
    lng_deg = np.array([int(p[5:7]) for p in pentads])
    lng_min = np.array([int(p[7:9]) for p in pentads])
    quadrant = np.array([p[4] for p in pentads])
    
    # Calculate absolute values
    lat_abs = lat_deg + lat_min / 60
    lng_abs = lng_deg + lng_min / 60
    
    # Cell size
    d = 5 / 60
    
    # Decode signed northwest corner; zero longitude has no western offset.
    lat_north = np.where(np.isin(quadrant, ["_", "a"]), -lat_abs, lat_abs)
    lng_west = np.where(np.isin(quadrant, ["a", "b"]), -lng_abs, lng_abs)
    lat_centers = lat_north - d / 2
    lng_centers = lng_west + d / 2

    return lat_centers.tolist(), lng_centers.tolist()


# ============================================================================
# Geometric Operations
# ============================================================================

def pentad2polygon(pentads):
    """
    Returns the geometric bounding box (Polygon) for the given pentad ID(s).
    
    This function derives the polygon bounds directly from the pentad ID.
    Bounds follow the regular northwest-corner naming rule. For valid IDs,
    this agrees with latlng2polygon() at any point assigned to the cell.
    No website-specific label or geometry overrides are applied.
    
    Parameters:
    -----------
    pentads : str or list-like of str
        Pentad ID(s) (e.g., "2530_2750").
        
    Returns:
    --------
    shapely.geometry.Polygon or list of shapely.geometry.Polygon
        The pentad grid cell(s) as polygon(s).
    """
    is_scalar = isinstance(pentads, str)
    lats, lngs = pentad2latlng(pentads)  # Returns lists of centers
    
    polys = latlng2polygon(lats, lngs)

    if is_scalar:
        return polys[0]
    return polys



def latlng2polygon(lat, lng):
    """
    Returns the exact pentad grid cell polygon containing the given coordinate(s).
    
    This uses the same northwest-corner grid and edge assignment as
    latlng2pentad(): (south, north] x [west, east). Polygon objects include
    their boundaries geometrically; point assignment uses the half-open rule.

    Parameters:
    -----------
    lat : float or array-like
        Latitude(s).
    lng : float or array-like
        Longitude(s).
    
    Returns:
    --------
    shapely.geometry.Polygon or list of Polygons
        The rectangular polygon(s) representing the grid cell(s).
    """
    lat = np.asarray(lat)
    lng = np.asarray(lng)
    scalar_input = lat.ndim == 0
    
    if scalar_input:
        lat = lat[np.newaxis]
        lng = lng[np.newaxis]
        
    north, west = _grid_nw_corner(lat, lng)
    minx = west / 12
    maxx = (west + 1) / 12
    miny = (north - 1) / 12
    maxy = north / 12

    polys = [box(x1, y1, x2, y2) for x1, y1, x2, y2 in zip(minx, miny, maxx, maxy)]
    
    if scalar_input:
        return polys[0]
    return polys


def generate_pentad_grid(geometry, return_geojson=True):
    """
    Generate pentads whose interiors overlap the given polygon geometry.
    
    This function creates a grid of pentad cells covering the bounding box
    of the input geometry, then filters to cells with positive-area overlap, excluding boundary-only contact.
    
    Parameters:
    -----------
    geometry : shapely.geometry or geopandas geometry
        The area to cover with pentads (Polygon, MultiPolygon, etc.).
    return_geojson : bool, default=True
        If True, returns GeoJSON string. If False, returns GeoDataFrame.
    
    Returns:
    --------
    str or geopandas.GeoDataFrame
        Pentad grid as GeoJSON string or GeoDataFrame with columns:
        - 'pentad': Pentad ID
        - 'geometry': Polygon geometry
    """
    # Get bounds
    minx, miny, maxx, maxy = geometry.bounds
    
    # Integer grid indices avoid accumulated floating-point arange errors.
    xs = (np.arange(np.floor(minx * 12), np.ceil(maxx * 12)) + 0.5) / 12
    ys = (np.arange(np.floor(miny * 12), np.ceil(maxy * 12)) + 0.5) / 12

    # Create meshgrid of centers
    xx, yy = np.meshgrid(xs, ys)
    xx = xx.flatten()
    yy = yy.flatten()
    
    # Vectorized creation of polygons and IDs
    polys = latlng2polygon(yy, xx)
    ids = latlng2pentad(yy, xx)
    
    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame(
        {'pentad': ids, 'geometry': polys}, 
        crs='EPSG:4326'
    )
    
    # Filter by intersection with the geometry
    # Using spatial index if available or just boolean indexing
    gdf = gdf[gdf.intersects(geometry) & ~gdf.touches(geometry)]
    
    if return_geojson:
        return gdf.to_json()
    else:
        return gdf
