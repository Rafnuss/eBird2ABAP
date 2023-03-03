# Notes on eBird checklists to ABAP card

The aims is to produce a datase of full protocl ABAP card from eBird EBD dataset.

## Process

1. Construct the card list
   1. Filter checklist which contribute to a valid card
      1. Only complete checklists
      2. Spatial: within pentad
         1. exlclude traveling with distance greater than
         2. Historical which don't have a distance
      3. Duration greated than 0.
   2. Group checklist by date (checkday)
   3. Loop over each pentad_observer
      1. Iterate through all checkday in increasing date order i
         1. Find the next checkday over the following 4 days f
            1. If valid (ie., sum(duration over the following 4 days)>2hr). create the card (pentad_observer_date) and i = i + f + 1
            2. If invalid, move to i = i+1 check
2. Add checklists to card
   1. Loop through card
      1. Add checklists which are: (1) within pentad, (2) same observer and (3) day within the 5 day period.
3. Add species level information to cards
   1. Loop through each card
      1. Filter by checklists.

## Sample ouput

```{js}
[
    {
        "CardNo": "0315_4000_obsr96453_19730717",
        "StartDate": "1973-07-17",
        "EndDate": "1973-07-17",
        "StartTime": null, :danger:
        "Pentad": "0315_4000",
        "ObserverNo": "obsr96453",
        "TotalHours": 3,
        "Hour1": , :danger:
        "Hour2": , :danger:
        ...,
        "TotalSpp": 13,
        "InclNight": 0, :danger:
        "AllHabitats": 0, :danger:
        "Checklists": ["S34208535", ... ],
        "TotalDistance":

        "Species": [
            "Andropadus importunus",
            "Apaloderma narina",
            ...

        ]
    },
    ...
]
```

## Key message

Checklists lost by filtering for valid pentad:

- 12% lost by historical without distance.
- 40% lost by complete.
- 30% lost by pentad restriction.
- 40% lost without duration.

-> 17K checklists (23% of the 90K) kept after filter (most of the filtering percentage are ovelaping).
-> 3K cards.
-> 10K can be match to a valid card.

## Needs to be done

- duplicate observers -> exact species list?
- Taxonomy matching -> ADU number.
- InclNight: Check each checklist for being spanning over night.
- AllHabitats: User input
- keep GLOBALUNIQUEIDENTIFIER?

## What eBird app could do

- use the track to determine pentad overlap
- Let the user confirm that a checklit belong to a single pentad rather than a check based on distance
