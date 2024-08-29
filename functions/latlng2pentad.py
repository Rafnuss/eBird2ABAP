def latlng2pentad(lat, lng):
    """
    Converts latitude and longitude coordinates into pentads, a 5-minute by 5-minute grid reference.

    Parameters:
    -----------
    lat : list or array-like of float
        A list or array of latitude values. Positive values represent the northern hemisphere, and negative values represent the southern hemisphere.
    lng : list or array-like of float
        A list or array of longitude values. Positive values represent the eastern hemisphere, and negative values represent the western hemisphere.

    Returns:
    --------
    list of str
        A list of strings where each string represents a pentad in the format "XXYYcZZWW", where:
        - XX: Degrees of latitude (2 digits).
        - YY: Minutes of latitude (2 digits).
        - c: Quadrant character (1 character). It can be:
            - '_': The point is in the northeastern quadrant (positive latitude and longitude).
            - 'a': The point is in the southwestern quadrant (negative latitude and longitude).
            - 'b': The point is in the southeastern quadrant (positive latitude, negative longitude).
            - 'c': The point is in the northwestern quadrant (negative latitude, positive longitude).
        - ZZ: Degrees of longitude (2 digits).
        - WW: Minutes of longitude (2 digits).

    Raises:
    -------
    TypeError
        If lat or lng are not list-like or if their lengths do not match.
    ValueError
        If lat or lng contain values outside the valid range for latitude (-90 to 90) or longitude (-180 to 180).

    Example:
    --------
    >>> lat = [-25.04166667, 34.08333333]
    >>> lng = [27.08333333, -29.04166667]
    >>> pentads = latlng2pentad(lat, lng)
    >>> print(pentads)  # Output: ['2530_a2750', '3435b2925']
    """
    import numpy as np

    lat = np.array(lat)
    lng = np.array(lng)

    # Input validation
    if len(lat) != len(lng):
        raise TypeError("Latitude (lat) and Longitude (lng) must have the same length.")
    if any(abs(x) > 90 for x in lat):
        raise ValueError("Latitude values must be between -90 and 90 degrees.")
    if any(abs(x) > 180 for x in lng):
        raise ValueError("Longitude values must be between -180 and 180 degrees.")

    lat = np.array(lat)
    lng = np.array(lng)

    # Determine the quadrant character based on latitude and longitude signs
    letter = np.empty_like(lat, dtype=str)
    letter[(lat <= 0) & (lng > 0)] = "_"
    letter[(lat < 0) & (lng < 0)] = "a"
    letter[(lat > 0) & (lng < 0)] = "b"
    letter[(lat > 0) & (lng > 0)] = "c"

    # Adjust latitude and longitude for pentad conversion
    lat2 = np.abs(lat + 0.0001)
    lat2[lat > 0] += 5 / 60
    lng2 = np.abs(lng + 0.0001)
    latDeg = np.floor(lat2)
    lngDeg = np.floor(lng2)
    latSec = np.floor((lat2 - latDeg) * 60 / 5) * 5
    lngSec = np.floor((lng2 - lngDeg) * 60 / 5) * 5

    # Convert to pentad string format
    s = []
    for i, l in enumerate(letter):
        s.append(
            f"{int(latDeg[i]):02d}{int(latSec[i]):02d}"
            + l
            + f"{int(lngDeg[i]):02d}{int(lngSec[i]):02d}"
        )

    return s
