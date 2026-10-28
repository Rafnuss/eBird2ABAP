# Pentad naming and geometry

## Reference rule

A pentad spans five minutes of latitude and five minutes of longitude. Its identifier encodes the **northwest corner**. Starting from that corner, the cell extends south and east; its centre lies 2.5 minutes south and 2.5 minutes east. These directions do not change between hemispheres.

This follows independent project sources:

1. Brooks and Harebottle, [SABAP2 Data Management Software Instruction Manual, version 2](https://birdlifezimbabwe.org/Attachments/Sabap2/sabap2_dms_manual_v2.pdf), section 2.2, printed page 5. It defines the northwest-corner code and gives `2920_2935` as an example.
2. Brooks et al. (2022), [The African Bird Atlas Project: a description of the project and BirdMap data-collection protocol](https://doi.org/10.2989/00306525.2022.2125097), *Ostrich* 93(4), 223–232, protocol section, page 3 of the author-uploaded version. The northwest-corner definition was checked in the [author-uploaded full text](https://www.researchgate.net/publication/365170746_The_African_Bird_Atlas_Project_a_description_of_the_project_and_BirdMap_data-collection_protocol); the publisher's PDF endpoint returned HTTP 403 during this review.
3. The Biodiversity and Development Institute's [pentad explanation](https://thebdi.org/glossary/pentad/), which specifies the northwest corner and explains `b` for north/west and `c` for north/east, with Dakar and Jos examples. It also contains a directional typo calling the bottom-right corner southwest; that wording is not used as a geometric rule here.

The Larsen et al. (2009) paper already in `references/` describes **extended quarter-degree grid cells**, not this five-minute pentad identifier. Its hemisphere-dependent reference-corner convention is not a definition of pentad naming and must not be substituted for the SABAP2 rule.

## Coordinate assignment

With latitude `lat`, longitude `lng`, and cell width `d = 1/12` degree, the package uses:

```text
north = ceil(lat / d) * d
west  = floor(lng / d) * d
bounds = (west, north - d, west + d, north)
centre = (north - d/2, west + d/2)  # latitude, longitude
```

The encoder formats the absolute degree/minute values of those signed edges, rather than flooring the absolute input coordinates. This distinction fixes the former one-cell shifts north of the equator and west of Greenwich.

| Interior coordinate (latitude, longitude) | Correct ID |
| --- | --- |
| −25.04, 27.04 | `2500_2700` |
| 0.04, 10.04 | `0005c1000` |
| 4.375, −7.375 | `0425b0725` |
| −15.875, −5.625 | `1550a0540` |

`_` denotes south/east, `b` north/west, and `c` north/east. The package retains its existing `a` convention for south/west as a logical extension; the checked project sources did not explicitly establish this fourth separator. This is not presented as independently verified official nomenclature.

For valid regular IDs, `pentad2polygon(latlng2pentad(lat, lng)[0])` and `latlng2polygon(lat, lng)` now describe the same cell in all four quadrants. `pentad2latlng()` returns lists of centre coordinates, including for a single string input.

## Exact shared edges

The references do not prescribe which adjacent cell receives a point exactly on a shared edge. The package explicitly chooses the cell to the **south and east**:

```text
south < latitude <= north
west <= longitude < east
```

Thus latitude zero belongs to the southern row, longitude zero to the eastern column, and `(0, 0)` receives `0000_0000`. Values within 1e-10 grid units of an exact grid line are snapped to that line to remove floating-point arithmetic noise, a tolerance of about one micrometre at the equator. Points meaningfully on either side remain distinct. Shapely polygons themselves are closed geometric objects, so an edge can be covered by two polygons; the assignment rule gives the unique ID.

Generated grids contain cells with positive-area overlap with the requested polygon. Cells that merely touch its boundary are omitted. Integer grid indices avoid accumulated floating-point steps and ensure generated cell labels agree with their geometry.

## Published KML disagreements

The [official KML audit](pentad-kml-audit.md) found 293 label/geometry pairs that depart from the regular rule. Following the user's requested policy, the package follows the documented mathematical rule and does not add website-specific overrides. Published legacy labels should be retained in a separate source field when joining website data; they must not be assumed equivalent to the package's regular IDs for those 293 cells.

After correction, the encoder agrees with all 372,206 regular cells in the supplied 372,499-cell KML. Its 293 remaining differences are exactly the independently identified name/geometry exceptions. Correcting those cells' names from their polygon edges gives round trips under the same regular rule; this does not prove how their legacy labels arose.

This change affects northern/western assignments, equator/meridian edge cases, and previously generated grids and card identifiers. Regenerate derived outputs when using the corrected code. Tests cover published examples, all four quadrants, exact edges, 5,000 deterministic random points, generated grids, and downstream checklist eligibility. Full-globe use beyond two-digit longitude degrees and polar cells remains outside the verified identifier format.
