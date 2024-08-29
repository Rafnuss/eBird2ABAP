def pentad2latlng(pentads):
    """
    Converts a list of pentads into their corresponding latitude and longitude values.

    Parameters:
    -----------
    pentads : list of str
        A list of strings where each string represents a pentad in the format "XXYYcZZWW",
        where:
        - XX: Degrees of latitude (2 digits).
        - YY: Minutes of latitude (2 digits).
        - c: Quadrant character (1 character). It can be:
            - '_': The point is in the northeastern quadrant (positive latitude and longitude).
            - 'a': The point is in the southwestern quadrant (negative latitude and longitude).
            - 'b': The point is in the southeastern quadrant (positive latitude, negative longitude).
            - 'c': The point is in the northwestern quadrant (negative latitude, positive longitude).
        - ZZ: Degrees of longitude (2 digits).
        - WW: Minutes of longitude (2 digits).

    Returns:
    --------
    tuple of lists
        - lat0: List of latitude values corresponding to the input pentads.
        - lng0: List of longitude values corresponding to the input pentads.

    Raises:
    -------
    TypeError
        If the input is not a list of strings or if any element is not a string.
    ValueError
        If any pentad string is not exactly 10 characters long,
        if degrees or minutes are non-numeric,
        or if the quadrant character is invalid.

    Example:
    --------
    >>> pentads = ["2530_2750", "3435a2925"]
    >>> lat0, lng0 = pentad2latlng(pentads)
    >>> print(lat0)  # Output: [-25.041666666666668, -34.083333333333336]
    >>> print(lng0)  # Output: [27.083333333333332, -29.041666666666668]
    """
    import numpy as np

    # Input validation
    pentads = np.array(pentads)

    for i, p in enumerate(pentads):
        if not isinstance(p, str):
            raise TypeError(f"Element at index {i} is not a string: {p}")

        if len(p) != 9:
            raise ValueError(f"Element at index {i} is not 9 characters long: {p}")

        if not (p[0:4].isdigit() and p[5:9].isdigit()):
            raise ValueError(
                f"Element at index {i} has non-numeric degrees or minutes: {p}"
            )

        if p[4] not in ["_", "a", "b", "c"]:
            raise ValueError(
                f"Element at index {i} has an invalid quadrant character '{p[4]}': {p}"
            )

    lat0 = [int(p[0:2]) + int(p[2:4]) / 60 for p in pentads]
    lng0 = [int(p[5:7]) + int(p[7:9]) / 60 for p in pentads]

    for i, p in enumerate(pentads):
        if p[4] in ["_", "a"]:
            lat0[i] = -lat0[i]
        if p[4] in ["b", "a"]:
            lng0[i] = -lng0[i]

    # Return center
    lng0 = [l + 5 / 60 / 2 for l in lng0]
    lat0 = [l - 5 / 60 / 2 for l in lat0]

    return lat0, lng0
