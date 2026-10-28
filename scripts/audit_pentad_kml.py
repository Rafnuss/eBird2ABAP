"""Compare published KML pentads with package conversions and NW-corner naming.

Run with: uv run python scripts/audit_pentad_kml.py /path/to/all_download.kml /tmp/pentad-audit
The KML is read as data. Outputs are diagnostic CSV files, not a renamed atlas grid.
"""

import argparse
import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

from eBird2ABAP import latlng2pentad, pentad2latlng

# Read official cell names and geometry ------------------------------------
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("kml", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
namespace = "{http://www.opengis.net/kml/2.2}"
rows = []
for _, element in ET.iterparse(args.kml, events=("end",)):
    if element.tag == namespace + "Placemark":
        points = [tuple(map(float, p.split(",")[:2]))
                  for p in element.find(".//" + namespace + "coordinates").text.split()]
        xs, ys = zip(*points)
        rows.append((element.findtext(namespace + "name"), min(xs), min(ys), max(xs), max(ys)))
        element.clear()

cells = pd.DataFrame(rows, columns=["pentad", "minx", "miny", "maxx", "maxy"])
lat = (cells.miny + cells.maxy) / 2
lng = (cells.minx + cells.maxx) / 2

# Compare existing package behavior at cell centres -----------------------
cells["package_id"] = latlng2pentad(lat, lng)
decoded_lat, decoded_lng = pentad2latlng(cells.pentad)
cells["encoding_match"] = cells.pentad.eq(cells.package_id)
# Some KML vertices are rounded to four decimals, about 5 metres at the equator.
cells["decoding_match"] = np.isclose(lat, decoded_lat, rtol=0, atol=0.000051) & np.isclose(lng, decoded_lng, rtol=0, atol=0.000051)

# Derive the regular NW-corner name independently from KML bounds ----------
# Round published edges to the nearest five-minute grid line.
north_minutes = np.rint(cells.maxy * 12).astype(int) * 5
west_minutes = np.rint(cells.minx * 12).astype(int) * 5
quadrant = np.where(lat > 0, np.where(lng > 0, "c", "b"), np.where(lng > 0, "_", "a"))
cells["nw_corner_id"] = [
    f"{abs(y) // 60:02d}{abs(y) % 60:02d}{q}{abs(x) // 60:02d}{abs(x) % 60:02d}"
    for y, x, q in zip(north_minutes, west_minutes, quadrant)
]
exceptions = cells.loc[cells.pentad.ne(cells.nw_corner_id)].copy()
exceptions["difference"] = np.where(
    (exceptions.pentad.str[4] == "c") & (exceptions.minx < 0), "c label west of Greenwich",
    np.where((exceptions.pentad.str[4] == "_") & (exceptions.minx < 0),
             "_ label west of Greenwich", "other name/corner difference"),
)

# Save inspectable results and source fingerprint -------------------------
args.output.mkdir(parents=True, exist_ok=True)
cells.to_csv(args.output / "cell_comparison.csv", index=False)
exceptions.to_csv(args.output / "name_geometry_exceptions.csv", index=False)
with args.kml.open("rb") as stream:
    fingerprint = hashlib.file_digest(stream, "sha256").hexdigest()
summary = (
    f"Input: {args.kml.name}\nSHA256: {fingerprint}\n"
    f"Cells: {len(cells)}\nUnique IDs: {cells.pentad.nunique()}\n"
    f"Package encoding matches: {cells.encoding_match.sum()}\n"
    f"Package decoding matches (0.000051 degree tolerance): {cells.decoding_match.sum()}\n"
    f"Regular NW-corner name matches: {len(cells) - len(exceptions)}\n"
    f"Name/geometry exceptions: {len(exceptions)}\n"
    + exceptions.groupby("difference").size().to_string() + "\n"
)
(args.output / "summary.txt").write_text(summary, encoding="utf-8")
print(summary)
