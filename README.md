[![PyPI version](https://img.shields.io/pypi/v/eBird2ABAP.svg)](https://pypi.org/project/eBird2ABAP/) [![GitHub stars](https://img.shields.io/github/stars/Rafnuss/eBird2ABAP.svg?)](https://github.com/Rafnuss/eBird2ABAP)

# eBird to ABAP

[View on GitHub](https://github.com/RaphaelNussbaumer/eBird2ABAP)

The aims of this python package is to produce a dataset of ABAP full protocol card equivalent from the eBird EBD dataset.

The overview process is to find and combine eBird checklists that satisfy the full protocol requirements: same observers, within a pentad, at least 2hr of reporting all species spread over 5 days.

This process does not address "ad hoc" data (e.g., incomplete data in eBird).

## Getting started

### Installation

Install the package from PyPI:

```bash
pip install eBird2ABAP
```
### Usage

#### Convert eBird data to ABAP cards

Download EBD:

```bash
wget https://ebird.org/data/download?p=prepackaged/ebd_AFR_relJul-2024.tar
```

Run the function:

```python
ebird2abap("data/eBird/ebd_AFR_relJul-2024/ebd_AFR_relJul-2024.txt.gz")
```

#### Pentad utilities

This package also includes several functions to work with pentads. See `notebook/pentad_naming_conventions.ipynb` for more details.

#### Generate pentad grid for a region

See `notebook/pentad_generation_test.ipynb` for more details

## Process

1. Construct the list of valid cards
   1. Group raw EBD data to checklist level information (merge shared checklist)
   2. Filter checklists which could make a valid card
      1. Keep only complete checklists
      2. Keep only checklists with `Historical`, `Stationary`, `Traveling`, `Incidental` protocol
      3. Keep only checklists within the pentad, that is,
         1. Exclude checklists with `historical` protocol that don't have a distance.
         2. Exclude checklists with distance greater than the distance from center of checklist to closest pentad limit (accept some overlap with a correction factor).
      4. Keep only checklists with duration greated than 0.
   3. Group checklists by date (named `checkday` later on)
   4. Group checklists into pentad_observer group so that we only have to loop through the date to find valid card
   5. Preliminary filter to eliminate all pentad_observer for which the sum over the entire period does not lead to 2h
   6. For each remaining pentad_observer, apply the function `checkday_pentad_observer()`, which,
      1. Compute the temporal distance between all checkday and check if they are within 5 days.
      2. Loop through all checkday,
         1. Compute the total duration of all checkdays within temporal distance
            1. If valid, create the card_id and apply it to all checkday. Iterate to the first next checkday that was not within temporal distance
            2. If invalid, iterate to the next checkday
2. Create the card data
   1. For each valid card, aggregate all checklists which are (1) within pentad, (2) same observer and (3) day within the 5 day period. This include more checklists than used to construct the list of valid cards
3. Add species level information to cards
   1. Add sequence information based on first occurance on checklist.
4. Export in JSON

## Matching entry

### Card level

|                   | **Example**                 | **eBird EBD**                  | **Comments**                                                   |
| ----------------- | --------------------------- | ------------------------------ | -------------------------------------------------------------- |
| **Protocol**      | "F"                         | "F"                            | Only full card are considered in this conversion process       |
| **ObserverEmail** | "ipanshak@gmail.com"        | "kenyabirdmap@naturekenya.org" | Using KBM email adress for now                                 |
| **CardNo**        | "0910c0725_050642_20230815" | _Pentad_ObserverNo_StartDate_  | build from Prend, ObserverNo and start date.                   |
| **StartDate**     | "2023-08-14"                | min(OBSERVATIONDATE)           |                                                                |
| **EndDate**       | "2023-08-17"                | max(OBSERVATIONDATE)           |                                                                |
| **StartTime**     | "06:43"                     | min(OBSERVATIONDATETIME)       |                                                                |
| **Pentad**        | "0910c0725"                 | card_pentad                    |                                                                |
| **ObserverNo**    | "050642"                    | "22829"                        | eBird account number is 22829 on ABAP.                         |
| **TotalHours**    | "1:57"                      | sum(DURATIONMINUTES)           | sum of the durations of all checklists                         |
| **Hour1**         | 14                          | ""                             | We don't record sequence in eBird                              |
| **Hour2**         | 23                          | ""                             |                                                                |
| **Hour3**         | 0                           | ""                             |                                                                |
| **Hour4**         | 0                           | ""                             |                                                                |
| **Hour5**         | 0                           | ""                             |                                                                |
| **Hour6**         | 0                           | ""                             |                                                                |
| **Hour7**         | 0                           | ""                             |                                                                |
| **Hour8**         | 0                           | ""                             |                                                                |
| **Hour9**         | 0                           | ""                             |                                                                |
| **Hour10**        | 0                           | ""                             |                                                                |
| **TotalSpp**      | 23                          | length(sp_list)                |                                                                |
| **InclNight**     | "0"                         | "0"                            | This conversion tool does not adress the issue of nocturnal    |
| **AllHabitats**   | "0"                         | "0"                            | This conversion tool does not quantify the use of all habitat. |
|                   |                             | Checklists                     | List of checklists used                                        |
|                   |                             | TotalDistance                  | sum of distances of all checklists                             |
|                   |                             | ObserverNoEbird                | observer ID from eBird                                         |

### Record level

|                  | **Example**                 | **eBird EBD**                 | **Comments**                                                                |
| ---------------- | --------------------------- | ----------------------------- | --------------------------------------------------------------------------- |
| **Sequence**     | 1                           | _i_                           | Taxonomic order                                                             |
| **Latitude**     | 9.0910404                   | checklist_latitude            | Not recorded                                                                |
| **Longitude**    | 7.4309485                   | checklist_longitude           | Not recorded                                                                |
| **Altitude**     | 469.8                       | ""                            | Not recorded                                                                |
| **CardNo**       | "0910c0725_050642_20230815" | _Pentad_ObserverNo_StartDate_ | Same as the card to which the record belong to                              |
| **Spp**          | 314                         | ADU                           | ADU number match based on <https://github.com/A-Rocha-Kenya/Birds-of-Kenya> |
| **Accuracy**     | 35.340999603271             | ""                            | Not recorded                                                                |
| **SightingTime** | "2023-08-15T05:36:33.834Z"  | checklist_start               | Use the checklist of the first occurance                                    |

## Sample ouput

```js
[
   {
      "Protocol":"F",
      "ObserverEmail":"kenyabirdmap@naturekenya.org",
      "CardNo":"0500b0220_r1034990_20180213",
      "StartDate":"2018-02-13",
      "EndDate":"2018-02-15",
      "StartTime":"15:08",
      "Pentad":"0500b0220",
      "ObserverNo":"22829",
      "TotalHours":2.0,
      "Hour1":"",
      "Hour2":"",
      "Hour3":"",
      "Hour4":"",
      "Hour5":"",
      "Hour6":"",
      "Hour7":"",
      "Hour8":"",
      "Hour9":"",
      "Hour10":"",
      "TotalSpp":38,
      "InclNight":"0",
      "AllHabitats":"0",
      "Checklists":[
         "S43361123",
         "S43361118"
      ],
      "TotalDistance":0.0,
      "ObserverNoEbird":"obsr1034990",
      "records":[
         {
         "Sequence":1,
         "Latitude":4.9640506,
         "Longitude":-2.40952,
         "Altitude":"",
         "CardNo":"0500b0220_r1034990_20180213",
         "Spp":1338,
         "SourceSpp":,
         "Accuracy":"",
         "SightingTime":"2018-02-13T15:08:00Z"
         },
         ...
      ]
   },
   ...
]
```

## Discussion

- Support Ad-hoc?

What eBird/eBird user can do to improve/maximize the number of card?

- Both protocol need user to do complete list (and not add-hoc or incomplete).
- Try to encourage birder to avoid using Historical protocol
- Use the track to determine pentad overlap
- Let the user confirm that a checklit belong to a single pentad rather than a check based on distance
- User input for `AllHabitats`.
