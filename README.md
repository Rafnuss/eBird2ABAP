# eBird to ABAP

The aims is to produce a datase of full protocl ABAP card from eBird EBD dataset.

## Process

1. Construct the card list
   1. Group raw EBD data to checklist level information
   2. Filter checklistd which contribute to a valid card
      1. Only complete checklists
      2. Within pentad
         1. Exlclude traveling with distance greater than
         2. Historical which don't have a distance
      3. Duration greated than 0.
      4. Protocol is: "Historical", "Incidental", "Stationary", "Traveling"
   3. Group checklists by date (i.e.,checkday)
   4. Loop over each group pentad-observer
      1. Iterate through all checkday sorted by date `i`
         1. Find the next checkday over the following 4 days `f`
            1. If valid (ie., sum(duration over the following 4 days)>2hr). create the card (pentad_observer_date) and `i = i + f + 1`
            2. If invalid, move to `i = i+1` check
2. Add checklists to card
   1. Loop through all cards
      1. Add checklists which are: (1) within pentad, (2) same observer and (3) day within the 5 day period. This list of checklists is different from the one used to construc the card list.
3. Add species level information to cards
   1. Loop through each card
      1. Filter by checklists
      2. Compute species level information. 

## Sample ouput

```{js}
[
    {
        "CardNo": "0315_4000_obsr96453_19730717",
        "StartDate": "1973-07-17",
        "EndDate": "1973-07-17",
        "StartTime": null, 
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

## Key number for Kenya

Checklists lost by filtering for valid pentad:

- 12% lost by historical without distance.
- 40% lost by complete.
- 30% lost by pentad restriction.
- 40% lost without duration.

-> 17K checklists (23% of the 90K) kept after filter (most of the filtering percentage are ovelaping).
-> 10K checklists can be match to a valid card.
-> 3K cards.


## Needs to be done

- Duplicate observers: Not sure what is happening on the EBD. Something to check. 
- Taxonomy matching: What do they want?  ADU number I suppose. Is there a match list for eBird at the global level (I have one for Kenya, but not for `ZA`)
- `InclNight`: Check each checklist start and end time for being spanning over night. Threashold of duration covering night time.
- `AllHabitats`: How to map? user input
- Should `GLOBALUNIQUEIDENTIFIER` be kept? 

## What would improve/maximize the number of card

- Use the track to determine pentad overlap
- Let the user confirm that a checklit belong to a single pentad rather than a check based on distance
- User input for `AllHabitats`.
