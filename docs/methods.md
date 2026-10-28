# Research methods

These are working analysis rules. The output is an inspectable atlas-card candidate, not a verified ABAP submission. Missing evidence is listed in [issues](issues.md); taxonomy has its own [update notes](taxonomy.md).

## Shared observations

The [eBird best-practices guide](https://ebird.github.io/ebird-best-practices/ebird.html#sec-ebird-import-shared) and [`auk_unique()`](https://cornelllabofornithology.github.io/auk/reference/auk_unique.html) treat a shared group as one independent event. We retain the union of taxa, choose representative metadata from the lowest checklist ID, and retain all source checklist/observer IDs in aligned checklist-ID order. Ordering is lexical, not a claim about submission timestamps.

The taxon key is the original Avibase concept ID. There is no parent-species roll-up. Source duration, start, protocol, completeness, or location disagreements set `SHARED METADATA CONFLICT`; these events cannot contribute to a card until reviewed. We do not manufacture a coherent checklist by selecting the largest duration, most complete report, or different fields from different participants.

`read_EBD(..., return_members=True)` returns observations plus the original member metadata. `EVENT ID` is the group ID or the unshared sampling-event ID. Card grouping uses the representative observer; it does not give every participant a separate card or establish equal participation. A prefix can omit members, so only a full input establishes the complete available group union.

## Effort and card windows

The project owner selected complete **Stationary/Traveling** events with known start, positive duration, no metadata conflict, and passing spatial screen as qualifying effort. Historical/Incidental and incomplete lists may supplement an established card's observations when spatially supported, but cannot inflate qualifying hours or distance.

Time is an interval union within representative observer/pentad: 06:00–07:00 plus 06:30–07:30 is 90 minutes. Intervals split at midnight. Exactly 120 minutes within `[start date, start date + 5 days)` qualifies. Failed windows advance one observed date; successful windows consume their dates and remain non-overlapping. Card starts must be dates when a qualifying checklist began. Overlap between different pentads is flagged for review rather than silently allocated; see the issue list.

Missing starts stay unknown. The imported date field is normalized to calendar date because Project 1056 can supply a noon component. Card metadata includes known effort end, clipped to the five-day endpoint. A known zero distance remains zero; a missing qualifying distance makes the total unknown. Nonzero route distances cannot be prorated when timers overlap or effort is clipped.

`Accuracy`, `Sequence`, `InclNight`, and `AllHabitats` remain unknown. Travel distance is not GPS accuracy; EBD list order is not true species-detection order. `RecordIndex` gives a deterministic processing order, and `SightingTimeBasis=checklist_start` labels the available time correctly. Avibase keys are not ADU codes. Receiving-account values stay unknown unless explicitly provided.

## Spatial screen

The [eBird protocols](https://support.ebird.org/en/support/solutions/articles/48000950859) describe Stationary activity as staying within approximately 30 m and Traveling as movement with a known distance. [Selected localities](https://support.ebird.org/en/support/solutions/articles/48000850891) may be hotspots or adjusted points, not route starts.

Compute WGS84 geodesic distance to the four pentad edges. Stationary uses a 30 m radius, or a larger reported distance; missing distance remains missing in the output. Other protocols require known distance. A radius fitting inside the cell is `screen_pass`; otherwise `possible_boundary_crossing`, or `unknown_distance` when unsupported. The former 0.8 straight-line correction and 20% boundary allowance are removed.

This is conditional, conservative screening, not track validation. A pass cannot prove the observations stayed inside; a failure does not prove they crossed. Exact decisions need a track or independent field evidence.

## Pentad naming

The [SABAP2 manual, section 2.2, page 5](https://birdlifezimbabwe.org/Attachments/Sabap2/sabap2_dms_manual_v2.pdf), [Brooks et al. (2022)](https://doi.org/10.2989/00306525.2022.2125097), and [BDI explanation](https://thebdi.org/glossary/pentad/) define the northwest corner. The paper was verified in its [author-uploaded full text](https://www.researchgate.net/publication/365170746_The_African_Bird_Atlas_Project_a_description_of_the_project_and_BirdMap_data-collection_protocol); the publisher PDF returned HTTP 403. The BDI explanation confirms `b` north/west and `c` north/east, though its bottom-right directional wording contains a typo. The package retains `a` for south/west as a logical extension not explicitly established by the checked sources.

For `d = 1/12` degree:

```text
north = ceil(latitude / d) * d
west = floor(longitude / d) * d
bounds = (west, north - d, west + d, north)
centre = (north - d/2, west + d/2)  # latitude, longitude
```

Cells always extend south/east, independent of hemisphere. Shared edges are assigned south/east: `(south, north]` by `[west, east)`. The references do not prescribe edge assignment; this deterministic rule is a project choice. Floating noise within 1e-10 grid units of a line is snapped to it. Generated grids omit boundary-only contacts.

| Interior point (latitude, longitude) | ID |
| --- | --- |
| −25.04, 27.04 | `2500_2700` |
| 0.04, 10.04 | `0005c1000` |
| 4.375, −7.375 | `0425b0725` |
| −15.875, −5.625 | `1550a0540` |

The Larsen et al. (2009) paper in `references/` concerns extended quarter-degree cells, not this five-minute naming rule; its hemisphere-dependent corner must not be substituted here.

## KML audit evidence

The supplied `all_download.kml` came from [BirdMap coverage](https://www.birdmap.africa/coverage), [official KML download](https://api.birdmap.africa/sabap2/v2/pentads/all/download?period=&dates=&format=KML). SHA256: `d8a261a8505730e21556451e2ddb56ebac67f143bcc33f3c98cec4cec4594abd`.

Of 372,499 unique cells, 372,206 labels follow the rule. All 372,499 geometry-derived logical IDs round-trip and reconstruct the polygons within 0.000051 degrees, accommodating published rounding. The other 293 labels comprise 278 eastern (`c`) labels immediately west of Greenwich, 12 southern/eastern (`_`) labels on western Atlantic islands, and three latitude-label differences (`0440c0530`, `0450c0525`, `0505c0520`).

Spot checks of the live geometry API confirmed exceptions for [Ghana](https://api.birdmap.africa/sabap2/v2/pentads/pentad/0540c0005?format=geoJSON), [the southern Atlantic](https://api.birdmap.africa/sabap2/v2/pentads/pentad/1550_0540?format=geoJSON), and [Nigeria](https://api.birdmap.africa/sabap2/v2/pentads/pentad/0440c0530?format=geoJSON). The Nigerian page-centre metadata also disagreed with its polygon. Historical reasons remain unknown.

Follow the logical rule, as requested; no label exceptions are hard-coded. Keep source website IDs separately when joining those exceptional cells. Re-run the comparison with `uv run python scripts/audit_pentad_kml.py /path/to/all_download.kml /tmp/pentad-audit`. Regenerate grids/cards made by the old northern/western encoder.
