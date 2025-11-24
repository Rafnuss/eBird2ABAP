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

def _get_nw_corner(lat, lng):
    """
    Compute the NW corner components of the pentad grid cell containing a point.
    
    Returns the degrees and minutes that represent:
    - North edge (furthest from equator in absolute terms)
    - West edge (closest to prime meridian in absolute terms)
    
    This is a helper function that encapsulates the core pentad grid computation.
    
    Parameters:
    -----------
    lat : float or array-like
        Latitude(s).
    lng : float or array-like
        Longitude(s).
        
    Returns:
    --------
    tuple
        (lat_deg, lng_deg, lat_min, lng_min) as integers/arrays of integers.
    """
    # Ensure inputs are arrays
    lat = np.asarray(lat)
    lng = np.asarray(lng)
    
    # Calculate absolute values
    absLat = np.abs(lat)
    absLng = np.abs(lng)
    
    # Calculate degrees
    latDeg = np.floor(absLat).astype(int)
    lngDeg = np.floor(absLng).astype(int)
    
    # Calculate minutes
    latMin = (absLat - latDeg) * 60
    lngMin = (absLng - lngDeg) * 60
    
    # Calculate pentad minutes (0, 5, 10, ..., 55)
    # We use floor to find the start of the 5-minute interval
    latSec = (np.floor(latMin / 5) * 5).astype(int)
    lngSec = (np.floor(lngMin / 5) * 5).astype(int)
    
    return latDeg, lngDeg, latSec, lngSec


def latlng2pentad(lat, lng):
    """
    Convert latitude and longitude coordinates to pentad IDs.
    
    The pentad ID is a unique identifier for a 5' x 5' grid cell.
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
    scalar_input = False
    if lat.ndim == 0 and lng.ndim == 0:
        lat = lat[np.newaxis]
        lng = lng[np.newaxis]
        scalar_input = True
        
    # Input validation
    if lat.shape != lng.shape:
        raise ValueError("Latitude and longitude arrays must have the same shape.")
    if np.any(np.abs(lat) > 90):
        raise ValueError("Latitude values must be between -90 and 90 degrees.")
    if np.any(np.abs(lng) > 180):
        raise ValueError("Longitude values must be between -180 and 180 degrees.")
    
    # Compute pentad grid cell
    latDeg, lngDeg, latSec, lngSec = _get_nw_corner(lat, lng)
    
    # Determine the quadrant character based on latitude and longitude signs
    letter = np.empty_like(lat, dtype=str)
    letter[(lat <= 0) & (lng > 0)] = "_"
    letter[(lat <= 0) & (lng <= 0)] = "a"
    letter[(lat > 0) & (lng <= 0)] = "b"
    letter[(lat > 0) & (lng > 0)] = "c"
    
    # Convert to pentad string format (vectorized)
    if np.isscalar(latDeg):
        # Single value case
        return [f"{int(latDeg):02d}{int(latSec):02d}{letter}{int(lngDeg):02d}{int(lngSec):02d}"]
    else:
        # Array case
        pentad_ids = [
            f"{int(latDeg[i]):02d}{int(latSec[i]):02d}{letter[i]}{int(lngDeg[i]):02d}{int(lngSec[i]):02d}"
            for i in range(len(lat))
        ]
        return pentad_ids


# ============================================================================
# Helper Functions
# ============================================================================

def pentad2latlng(pentads):
    """
    Converts pentad IDs to their center latitude and longitude coordinates.
    
    The pentad ID represents the NW corner of the grid cell.
    The center is calculated by moving 2.5 arcminutes east and 2.5 arcminutes
    toward the equator from this corner.
    
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
    >>> print(lat)  # Output: [-25.54166667, -34.625]
    >>> print(lng)  # Output: [27.875, -29.45833333]
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
    
    # Calculate signed NW corner coordinates based on quadrant
    lat_north = np.zeros_like(lat_abs)
    lng_west = np.zeros_like(lng_abs)
    
    for i, q in enumerate(quadrant):
        if q == '_':  # Southern + Eastern
            lat_north[i] = 0.0 if lat_abs[i] == 0 else -lat_abs[i]
            lng_west[i] = lng_abs[i]
        elif q == 'a':  # Southern + Western
            lat_north[i] = 0.0 if lat_abs[i] == 0 else -lat_abs[i]
            lng_west[i] = -lng_abs[i] if lng_abs[i] > 0 else -d
        elif q == 'b':  # Northern + Western
            lat_north[i] = lat_abs[i]
            lng_west[i] = -lng_abs[i] if lng_abs[i] > 0 else -d
        else:  # 'c': Northern + Eastern
            lat_north[i] = lat_abs[i]
            lng_west[i] = lng_abs[i]
    
    # Half pentad size (2.5 arcminutes)
    half_d = d / 2
    
    # Calculate centers: move 2.5' east and 2.5' toward equator from NW corner
    lat_centers = lat_north - half_d  # Always move toward equator (decrease absolute value)
    lng_centers = lng_west + half_d   # Always move east (increase value)

    return lat_centers.tolist(), lng_centers.tolist()


# ============================================================================
# Geometric Operations
# ============================================================================

def pentad2polygon(pentads):
    """
    Returns the geometric bounding box (Polygon) for the given pentad ID(s).
    
    This function derives the polygon bounds directly from the pentad ID.
    Note that because the pentad naming convention involves specific adjustments
    (e.g., for points on boundaries), the polygon returned by this function
    represents the "named" cell, which corresponds to the ID.
    
    For exact geometric bounds of a coordinate without naming adjustments,
    use `latlng2polygon` instead.
    
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
    
    # Half-width in degrees (2.5 minutes)
    d_half = (5 / 60) / 2
    
    polys = []
    for lat, lng in zip(lats, lngs):
        minx = lng - d_half
        maxx = lng + d_half
        miny = lat - d_half
        maxy = lat + d_half
        polys.append(box(minx, miny, maxx, maxy))
        
    if is_scalar:
        return polys[0]
    return polys



def latlng2polygon(lat, lng):
    """
    Returns the exact pentad grid cell polygon containing the given coordinate(s).
    
    PRECISION NOTE:
    Unlike `latlng2pentad`, this function calculates the *exact* geometric
    boundaries of the 5'x5' grid cell containing the point, IGNORING the
    SABAP2 naming convention adjustments (which shift edge points).
    
    Use this function when you need the precise spatial footprint of the grid
    cell containing a specific point, rather than its label.
    
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
        
    # Compute grid cell (absolute)
    lat_deg, lng_deg, lat_min, lng_min = _get_nw_corner(lat, lng)
    
    # Absolute start (closest to zero)
    abs_lat0 = lat_deg + lat_min / 60
    abs_lng0 = lng_deg + lng_min / 60
    
    d = 5/60
    
    # Calculate bounds
    # If val >= 0: [abs0, abs0 + d]
    # If val < 0:  [-(abs0 + d), -abs0]
    
    miny = np.where(lat >= 0, abs_lat0, -(abs_lat0 + d))
    maxy = np.where(lat >= 0, abs_lat0 + d, -abs_lat0)
    
    minx = np.where(lng >= 0, abs_lng0, -(abs_lng0 + d))
    maxx = np.where(lng >= 0, abs_lng0 + d, -abs_lng0)
    
    polys = [box(x1, y1, x2, y2) for x1, y1, x2, y2 in zip(minx, miny, maxx, maxy)]
    
    if scalar_input:
        return polys[0]
    return polys


def generate_pentad_grid(geometry, return_geojson=True):
    """
    Generate all pentads that intersect with a given geometry.
    
    This function creates a grid of pentad cells covering the bounding box
    of the input geometry, then filters to only those that intersect it.
    
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
    
    # 5 minutes = 1/12 degree
    d = 5 / 60
    
    # Generate grid centers
    # We want to cover the entire bounding box.
    # Start at a multiple of d that is <= minx
    # End at a multiple of d that is >= maxx
    
    # Calculate start points (multiples of d)
    x_start = np.floor(minx / d) * d
    x_end = np.ceil(maxx / d) * d
    y_start = np.floor(miny / d) * d
    y_end = np.ceil(maxy / d) * d
    
    # Generate centers (start + d/2)
    xs = np.arange(x_start, x_end + d/2, d) + d/2
    ys = np.arange(y_start, y_end + d/2, d) + d/2
    
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
    gdf = gdf[gdf.intersects(geometry)]
    
    if return_geojson:
        return gdf.to_json()
    else:
        return gdf
