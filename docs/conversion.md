# Conversion reference

## Process

`ebird2abap()` transforms observation-level EBD data through a series of explicit tables. The normal regional EBD and African Bird Atlas Project 1056 exports use the same process after their protocol column is normalised.

| Stage | Main table | Purpose |
| --- | --- | --- |
| Read observations | `ebd` | One row per reported taxon on a checklist |
| Derive checklists | `chk` | One row per checklist, with pentad and effort checks |
| Test card eligibility | `checkday`, `card_valid` | Decide which observer/pentad/date combinations establish cards |
| Collect card checklists | `chk_card`, `card_chk` | Attach all spatially valid checklists in each card period |
| Create species records | `ebd_f_u` | Keep one observation per card and taxon concept |
| Format export | `card_exp` | Create ABAP card and record structures |

### 1. Read and normalise EBD observations

`read_EBD()` accepts an EBD `.txt`, `.txt.gz`, or a folder containing one of those files. It reads the fields used by the conversion. A standard EBD uses `PROTOCOL TYPE`; a Project 1056 export uses `PROTOCOL NAME`. The latter is renamed so downstream code sees one common `PROTOCOL TYPE` field.

Shared checklists are merged before conversion: records with the same `GROUP IDENTIFIER` are assigned the first sampling-event identifier in the group. Missing checklist start times are set to `00:00:00`, then `OBSERVATION DATETIME` is created and records are sorted chronologically.

### 2. Match taxa to ABAP species numbers

`add_ADU()` joins each EBD `TAXON CONCEPT ID` to `eBird2ABAP/matched_species.csv`, producing the ABAP species number `ADU`. This happens before card construction so the same matched observation table is carried through the workflow. A taxon concept with no mapping remains in the export with `ADU = 0`.

### 3. Make a checklist table and test spatial validity

`ebd2chk()` reduces observations to one row per `SAMPLING EVENT IDENTIFIER`. It calculates the SABAP pentad from the checklist coordinates and tests whether the checklist effort can fit within that pentad.

The spatial test uses the pentad centre, checklist location, reported effort distance, and two fixed corrections: 0.8 for effective straight-line distance and 1.2 for overlap. A checklist is spatially valid only when the resulting latitude and longitude extents both remain within the pentad limit. This is an approximate degree-based check, not a track or geodesic intersection.

The checklist table also stores protocol and completeness flags. The protocols that can establish a card are `Historical`, `Incidental`, `Stationary`, and `Traveling`. Checklists with missing effort distance are retained for the spatial test except Historical checklists, which are marked spatially invalid when effort distance is missing.

### 4. Establish card start dates from qualifying effort

`chk2valid_card()` first selects checklists that can establish a card. A qualifying checklist must be spatially valid, use an allowed protocol, have `DURATION MINUTES > 0`, and have `ALL SPECIES REPORTED = 1`.

Qualifying effort is summed by pentad, observer, and calendar date into `checkday`. Observer/pentad combinations with less than 120 minutes in total are discarded early. For each remaining group, the converter evaluates a forward interval `[start date, start date + 5 days)`. Exactly 120 minutes qualifies; a checklist on day six does not belong to that window.

When a window qualifies, all its qualifying dates are assigned to that card and the next window starts after it. When it fails, the next observed date is tested. Cards therefore do not overlap for a given observer/pentad. This fixes an earlier implementation that skipped all dates in failed windows and missed valid later cards. For example, 10 minutes on January 1 followed by 60 minutes each on January 5 and 6 now creates a card beginning January 5.

Window endpoints use sorted-date searches and cumulative effort rather than an all-pairs date matrix. No qualifying effort returns an empty card-selection table with the usual columns.

### 5. Attach the checklists that belong to each card

`valid_card2chk_card()` returns to the full checklist table. For every valid card start date, it attaches all spatially valid checklists from the same observer and pentad dated from the start date up to, but not including, five days later.

This is intentionally broader than the eligibility step:

| Role | Checklist requirements |
| --- | --- |
| Establish a card | spatially valid, allowed protocol, complete, and positive duration; contributes to the 120-minute threshold |
| Belong to an established card | spatially valid, same observer and pentad, and within the card's five-day interval |

Consequently, a checklist can contribute observations and effort to an existing card even if it was incomplete, used another protocol, or had zero duration. It cannot on its own create a card.

### 6. Aggregate card metadata

`chk_card2card_chk()` combines the attached checklists into one card row. It stores the list of sampling-event identifiers, earliest and latest observation datetimes, summed duration, and summed effort distance, alongside the pentad and eBird observer identifier.

### 7. Create one record for each taxon in each card

`chk_card2ebd_f_u()` filters the observation table to the checklists attached to cards, assigns their card identifier, sorts by observation time, and retains the first observation for every `CARD` and `TAXON CONCEPT ID` pair. Thus each taxon concept appears once per card, at its first recorded time and location in that card.

`Sequence` is currently calculated by ranking `TAXON CONCEPT ID` values within a card. It is not taken from an eBird taxonomic-order column.

### 8. Format the ABAP export

`ebd_f_u2card_exp()` builds the final card and record data. Total hours are summed duration divided by 60, total distance is summed effort distance, and accuracy is effort distance converted from kilometres to metres. The package uses fixed values for the full-protocol flag, ABAP account details, hour fields, nocturnal effort, and all-habitats fields; review these values before an operational submission.

## Species matching

The EBD supplies `SCIENTIFIC NAME` and the Avibase-based `TAXON CONCEPT ID`. The package joins the taxon concept ID to the curated `eBird2ABAP/matched_species.csv` mapping to assign an ABAP species number (`ADU`).

For ordinary species, the taxon concept generally corresponds to `SCIENTIFIC NAME`. For `issf` records, it identifies the more specific subspecies or form, while `SCIENTIFIC NAME` remains the parent species. EBD has no `REPORT AS` field, and the current workflow does not roll subspecies up to a parent species. An unmatched concept receives `ADU = 0`.

## Card-level output

| Field | Derived from | Notes |
| --- | --- | --- |
| `Protocol` | fixed | `F` for full protocol |
| `ObserverEmail` | fixed project value | Review before using another account |
| `CardNo` | pentad, observer, start date | Generated card identifier |
| `StartDate`, `EndDate` | checklist datetimes | Earliest and latest checklist dates |
| `StartTime` | checklist datetime | Earliest checklist time |
| `Pentad` | checklist coordinates | SABAP pentad |
| `ObserverNo` | fixed project value | Review before using another account |
| `TotalHours` | summed `DURATION MINUTES` | Hours across card checklists |
| `TotalSpp` | retained EBD taxon concepts | Number of card taxa, including unmatched concepts with `ADU = 0` |
| `Checklists` | sampling event IDs | Checklists included in the card |
| `TotalDistance` | summed `EFFORT DISTANCE KM` | Across card checklists |
| `ObserverNoEbird` | `OBSERVER ID` | eBird observer identifier |
| `Hour1`–`Hour10`, `InclNight`, `AllHabitats` | fixed defaults | Not inferred from EBD |

## Record-level output

| Field | Derived from | Notes |
| --- | --- | --- |
| `Sequence` | `TAXON CONCEPT ID` rank | Current implementation ranks IDs within a card |
| `Latitude`, `Longitude` | EBD observation | First observation retained for a card/taxon concept |
| `Altitude` | fixed blank | Not supplied by EBD |
| `CardNo` | card identifier | Links record to the card |
| `Spp` | `ADU` | ABAP species number; `0` if unmatched |
| `SourceSpp` | `TAXON CONCEPT ID` | EBD/Avibase taxon concept |
| `Accuracy` | `EFFORT DISTANCE KM` | Converted to metres |
| `SightingTime` | observation datetime | First retained observation time |

## Limitations

- Ad hoc and incomplete checklists do not establish valid cards.
- Historical checklists without effort distance are excluded from pentad validation.
- Nocturnal effort and `AllHabitats` are not inferred.
- Pentad overlap uses a simple degree-based approximation rather than a geodesic track intersection.
- Subspecies are not automatically rolled up.
- Large EBD files are expected to be processed interactively and may require substantial memory.
