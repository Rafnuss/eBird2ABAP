def pentad2latlng(pentads):
    import numpy as np
    lat0 = [ int(p[0:2]) + int(p[2:4]) / 60 for p in pentads]
    lng0 = [ int(p[5:7]) + int(p[7:9]) / 60 for p in pentads]

    for (i, p) in enumerate(pentads):
        if (p[4] == "_") | (p[4] == "a"):
            lat0[i] = -lat0[i]

        if (p[4] == "b") | (p[4] == "a"):
            lng0[i] = -lng0[i]

    # return center
    lng0 = [l + 5 / 60 / 2 for l in lng0]
    lat0 = [l - 5 / 60 / 2 for l in lat0]

    return lat0, lng0
