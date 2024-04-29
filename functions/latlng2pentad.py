def latlng2pentad(lat, lng):

    import numpy as np

    lat = np.array(lat)
    lng = np.array(lng)

    letter = np.empty_like(lat, dtype=str)
    letter[(lat <= 0) & (lng > 0)] = '_'
    letter[(lat < 0) & (lng < 0)] = 'a'
    letter[(lat > 0) & (lng < 0)] = 'b'
    letter[(lat > 0) & (lng > 0)] = 'c'

    lat2 = np.abs(lat + 0.0001)
    lat2[lat > 0] += 5 / 60
    lng2 = np.abs(lng + 0.0001)
    latDeg = np.floor(lat2)
    lngDeg = np.floor(lng2)
    latSec = np.floor((lat2 - latDeg) * 60 / 5) * 5
    lngSec = np.floor((lng2 - lngDeg) * 60 / 5) * 5

    s=[]
    for i,l in enumerate(letter):
        s.append(f"{int(latDeg[i]):02d}{int(latSec[i]):02d}" + l + f"{int(lngDeg[i]):02d}{int(lngSec[i]):02d}")

    return s
