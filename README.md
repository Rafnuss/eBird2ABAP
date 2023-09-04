# eBird to ABAP

The aims of this code is to produce a dataset of ABAP full protocol card equivalent from the eBird EBD dataset.

The overview process is to find and combine eBird checklists that satisfy the full protocol requirements: same observers, within a pentad, at least 2hr of reporting all species spread over 5 days.

This process does not address "ad hoc" data (e.g., incomplete data in eBird); we should discuss how to support that as well if that is of interest to the ABAP.

## Process

1. Construct a list of valid cards
   1. Group raw EBD data to checklist level information
   2. Filter checklists which could make a valid card
      1. Keep only complete checklists
      2. Keep only checklists with `Historical`, `Stationary`, `Traveling` protocol
      3. Keep only checklists `within pentad`, that is,
         1. Exclude checklists with `traveling` protocol with distance greater than the distance from center of checklist to closest pentad limit.
         2. Exclude checklists with `historical` protocol that don't have a distance.
      4. Keep only checklists with duration greated than 0.
   3. Group checklists by date (named `checkday` later on)
   4. Loop over each possible pentad-observer group
      1. Iterate through all `checkday` sorted by date: `i`
         1. Find all `checkday` over the following 4 days `f`
            1. If valid (i.e., sum(duration over all `checkday`)>2hr), create the card (identified by `pentad_observer_date`) and set `i = i + f + 1`
            2. If invalid, move to `i = i+1`
2. Combine checklists into the valid cards
   1. Loop through all cards
      1. Add checklists which are: (1) within pentad, (2) same observer and (3) day within the 5 day period. This list of checklists is different from the one used to construct the list of valid card.
3. Add species level information to cards
   1. Loop through each card
      1. Filter by checklists
      2. Compute species level information.

## Matching entry

### Card level

|                   | **Example**                 | **eBird EBD**                  | **Comments**                                                                                                         |
| ----------------- | --------------------------- | ------------------------------ | -------------------------------------------------------------------------------------------------------------------- |
| **Protocol**      | "F"                         | "F"                            | Only full card are considered in this conversion process                                                             |
| **ObserverEmail** | "ipanshak@gmail.com"        | "kenyabirdmap@naturekenya.org" | Not sure how this email is used. It would need to be a permanant email to use. Not sure which one, probably not mine |
| **CardNo**        | "0910c0725_050642_20230815" | _Pentad_ObserverNo_StartDate_  | build from Prend, ObserverNo and start date.                                                                         |
| **StartDate**     | "2023-08-14"                | min(OBSERVATIONDATE)           |
| **EndDate**       | "2023-08-17"                | max(OBSERVATIONDATE)           |
| **StartTime**     | "06:43"                     | min(OBSERVATIONDATETIME)       |
| **Pentad**        | "0910c0725"                 | card_pentad                    |
| **ObserverNo**    | "050642"                    | "eBird"                        | eBird has also a unique ID for user. Can we use this one? observer                                                   |
| **TotalHours**    | "1:57"                      | sum(DURATIONMINUTES)           | sum of the durations of all checklists                                                                               |
| **Hour1**         | 14                          | ""                             | We don't record sequence in eBird                                                                                    |
| **Hour2**         | 23                          | ""                             |
| **Hour3**         | 0                           | ""                             |
| **Hour4**         | 0                           | ""                             |
| **Hour5**         | 0                           | ""                             |
| **Hour6**         | 0                           | ""                             |
| **Hour7**         | 0                           | ""                             |
| **Hour8**         | 0                           | ""                             |
| **Hour9**         | 0                           | ""                             |
| **Hour10**        | 0                           | ""                             |
| **TotalSpp**      | 23                          | length(sp_list)                |
| **InclNight**     | "0"                         | "0"                            | This conversion tool does not adress the issue of nocturnal                                                          |
| **AllHabitats**   | "0"                         | "0"                            | This conversion tool does not quantify the use of all habitat.                                                       |
|                   |                             | Checklists                     | List of checklists used                                                                                              |
|                   |                             | TotalDistance                  | sum of distances of all checklists                                                                                   |
|                   |                             | ObserverNoEbird                | observer ID from eBird                                                                                               |

### Record level

|                  | **Example**                 | **eBird EBD**                 | **Comments**                                     |
| ---------------- | --------------------------- | ----------------------------- | ------------------------------------------------ |
| **Sequence**     | 1                           | _i_                           | Not recorded in eBird, use the taxonomical order |
| **Latitude**     | 9.0910404                   | ""                            | Not recorded                                     |
| **Longitude**    | 7.4309485                   | ""                            | Not recorded                                     |
| **Altitude**     | 469.8                       | ""                            | Not recorded                                     |
| **CardNo**       | "0910c0725_050642_20230815" | _Pentad_ObserverNo_StartDate_ |
| **Spp**          | 314                         |                               |
| **Accuracy**     | 35.340999603271             | ""                            | Not recorded                                     |
| **SightingTime** | "2023-08-15T05:36:33.834Z"  | OBSERVATIONDATE(i)            | Use the checklist of the first occurance         |

## Sample ouput

```{js}
[
    {
        "Protocol": "F",
        "ObserverEmail": "kenyabirdmap@naturekenya.org",
        "CardNo": "0315_4000_obsr96453_19730717",
        "StartDate": "1973-07-17",
        "EndDate": "1973-07-17",
        "StartTime": "12:00",
        "Pentad": "0315_4000",
        "ObserverNo": "ebird",
        "TotalHours": 4,
        "Hour1": "",
        "Hour2": "",
        "Hour3": "",
        "Hour4": "",
        "Hour5": "",
        "Hour6": "",
        "Hour7": "",
        "Hour8": "",
        "Hour9": "",
        "Hour10": "",
        "TotalSpp": 13,
        "InclNight": "0",
        "AllHabitats": "0",
        "Checklists": "S34208535",
        "TotalDistance": 2,
        "ObserverNoEbird": "obsr96453",
        "Species": [
            316,
            319,
            387,
            393,
            413,
            423,
            438,
            551,
            558,
            579,
            627,
            725,
            766
        ]
    },
    ...
]
```

## Summury of the process

### for Kenya

Checklists lost by filtering for valid pentad:

- 12% lost by historical without distance.
- 40% lost by incomplete list (not reporting all species).
- ~30% lost by within pentad restriction.
- 40% lost without duration.
- 23K checklists (26% of the 90K) kept after this filtering (some of the checklists are filtered multiple time).
- 13K checklists can be match to a valid card (i.e., sum or duration >2hr)
- Process results in 4.2K cards.

### for South Africa

- 33K checklist matched to a valid card
- 14K cards.

## Discussion

General considerations:

- Duplicate observers: Not sure what is happening on the EBD. Something to check.
- Within pentad is currently estimated as (distance center of pentad to checklist location) + distance traveled < 1.2\*half of pentad resolution. The 1.2 is to be able to keep more data while accepting checklists which were just at the border of a pentad.
- Should `GLOBALUNIQUEIDENTIFIER` be kept?
- Code written in MATLAB but allows to be fast (vectorial computation: 4 min.)

What eBird/eBird user can do to improve/maximize the number of card?

- Both protocol need user to do complete list (and not add-hoc or incomplete).
- Try to encourage birder to avoid using Historical protocol
- Use the track to determine pentad overlap
- Let the user confirm that a checklit belong to a single pentad rather than a check based on distance
- User input for `AllHabitats`.
