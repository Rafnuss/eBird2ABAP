# Official pentad KML audit — 28 October 2026

## Conclusion

The supplied official KML resolves the missing reference in the project review. It confirms a coordinate-to-ID bug in the package and also shows why a mathematical naming formula alone cannot reproduce every published pentad. The user subsequently specified that the documented/logical rule should take precedence over possible website errors. Independent primary references confirm northwest-corner naming, and the package has now been corrected to use it. Website-specific exceptions are retained as audit differences, not naming overrides. See [the rule and sources](pentads.md).

No additional file or interpretation is needed from the user. The supplied KML is valuable validation evidence, but its exceptional labels are not treated as normative definitions.

## Source and reproducibility

- Website: [BirdMap coverage](https://www.birdmap.africa/coverage).
- Linked download: [Official all-pentad KML](https://api.birdmap.africa/sabap2/v2/pentads/all/download?period=&dates=&format=KML).
- Supplied local file: `/Users/rafnuss/Downloads/all_download.kml`.
- SHA256: `d8a261a8505730e21556451e2ddb56ebac67f143bcc33f3c98cec4cec4594abd`.
- The file contains 372,499 placemarks with 372,499 unique identifiers.

The file was parsed as XML data. Placemark names and polygon coordinates were compared with package outputs; document text was not treated as instructions. The large KML was not copied into the repository.

Run the independent audit from the repository root:

```bash
uv run --frozen python scripts/audit_pentad_kml.py /Users/rafnuss/Downloads/all_download.kml /tmp/pentad-audit
```

It writes a source fingerprint, per-cell comparison, and a separate exception table. Comparisons use cell interiors, so the reported naming differences do not depend on choosing a side of a shared boundary. A tolerance of 0.000051 degrees accommodates vertices rounded to four or five decimal places.

## The ordinary code bug

For regular cells, the identifier encodes the northwest corner: the northern latitude edge and western longitude edge. `latlng2pentad()` instead floors the absolute latitude and longitude, which chooses the wrong edge in the north and west.

| Interior point (latitude, longitude) | Existing package ID | KML ID |
| --- | --- | --- |
| 0.04, 10.04 | `0000c1000` | `0005c1000` |
| 4.375, -7.375 | `0420b0720` | `0425b0725` |

The first KML cell covers longitude 10.00000–10.08333 and latitude 0.00000–0.08333. Its name uses the north edge, 0°05′. The existing encoder uses 0°00′ instead. Passing that incorrect ID to the decoder then produces a polygon south of the equator. The typical displacement is one five-minute cell per affected axis, roughly 9.3 km north/south at the equator.

The old general statement that this was a boundary convention is therefore incorrect. The discrepancy occurs well inside cells.

## Full-file comparison before correction

| Check | Matches | Differences |
| --- | ---: | ---: |
| Existing encoder applied to each official cell centre | 121,885 | 250,614 |
| Existing decoder compared with official cell centres | 372,206 | 293 |
| Independently derive names from official northwest corners | 372,206 | 293 |

Thus the main widespread error is in coordinate-to-ID encoding. The existing decoder already agrees with almost all regular official cells, but does not account for the exceptional published labels.

## Published exceptions

The 293 name/geometry exceptions comprise:

| Type | Cells |
| --- | ---: |
| `c` quadrant labels on cells immediately west of Greenwich | 278 |
| `_` quadrant labels on southern Atlantic island cells west of Greenwich | 12 |
| Northern latitude labels inconsistent with the polygon's north edge | 3 |

For example, official `0540c0005` covers longitude −0.08333–0 and latitude 5.58333–5.66667. A regular northwest-corner formula would call it `0540b0005`, but the published ID is `0540c0005`. It must not be silently renamed if the output needs to join BirdMap records.

The three other exceptions are `0440c0530`, `0450c0525`, and `0505c0520`. Their polygons lie one cell south of the location implied by their names.

Spot checks against the live per-pentad geometry API confirmed the KML label/geometry pairs for three different exception types:

- [Ghana: `0540c0005`](https://api.birdmap.africa/sabap2/v2/pentads/pentad/0540c0005?format=geoJSON).
- [Southern Atlantic: `1550_0540`](https://api.birdmap.africa/sabap2/v2/pentads/pentad/1550_0540?format=geoJSON).
- [Nigeria: `0440c0530`](https://api.birdmap.africa/sabap2/v2/pentads/pentad/0440c0530?format=geoJSON).

This establishes that those examples are not merely artifacts of the downloaded file. It does not establish why the labels differ historically, and the other 290 exceptions were not individually queried online. The Nigeria summary page's map-centre coordinate also differed from its polygon API; use the actual published polygons rather than page-centre metadata as the geometry reference.

## Superseded initial recommendation

The initial proposal was to preserve all published KML identifiers through a grid lookup. The user's instruction to follow the official/logical rule supersedes that approach. The implemented correction instead uses signed northwest corners and keeps generated polygons and IDs coherent. The full file was re-audited after correction:

| Check after correction | Matches | Differences |
| --- | ---: | ---: |
| Encoder applied to official cell centres | 372,206 | 293 |
| Decoder compared with official cell centres | 372,206 | 293 |
| Independent regular northwest-corner name | 372,206 | 293 |

The encoder's remaining differences are exactly the independently derived 293 KML exceptions. No KML naming exceptions were hard-coded. Do not silently join regular IDs to published IDs in these exceptional cells; retain the source identifier separately when importing website records.

The published KML rounds coordinates, so a point extremely close to an edge needs an explicit assignment rule. That small numerical detail is separate from the one-cell displacement confirmed here. A documented deterministic edge rule is an implementation choice and does not require the user to explain atlas nomenclature.

## Final validation

All 372,499 IDs derived independently from the KML polygon corners round-trip through the corrected encoder/decoder and reconstruct their source bounds within 0.000051 degrees. The remaining 293 differences concern the published labels, not a failure to construct the regular geographic cells. The four pentad test scripts pass under Python 3.11 with pandas 3.0.5 and 2.2.3. No website submissions were made.
