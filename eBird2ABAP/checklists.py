"""Independent sampling events, membership provenance, and elapsed effort."""

import pandas as pd

EVENT_METADATA = [
    'LATITUDE', 'LONGITUDE', 'OBSERVATION DATE', 'OBSERVATION DATETIME',
    'PROTOCOL TYPE', 'DURATION MINUTES', 'EFFORT DISTANCE KM', 'ALL SPECIES REPORTED',
]
MEMBER_COLUMNS = ['EVENT ID', 'GROUP IDENTIFIER', 'SAMPLING EVENT IDENTIFIER', 'OBSERVER ID', *EVENT_METADATA]


def collapse_shared_checklists(ebd):
    """Union group taxa by concept ID; select lowest checklist ID deterministically.

    Retain all member IDs. Conflicting event metadata is flagged, not reconciled
    using a maximum duration/completeness or arbitrary input row ordering.
    Returns collapsed observations and an explicit member metadata table.
    """
    members = ebd[MEMBER_COLUMNS].drop_duplicates().sort_values('SAMPLING EVENT IDENTIFIER', kind='stable')
    representative = members.drop_duplicates('EVENT ID').copy()
    conflicts = members.groupby('EVENT ID')[EVENT_METADATA].nunique(dropna=False).gt(1).any(axis=1)
    representative['SHARED METADATA CONFLICT'] = representative['EVENT ID'].map(conflicts)
    provenance = members.groupby('EVENT ID').agg(**{
        'SOURCE CHECKLIST IDS': ('SAMPLING EVENT IDENTIFIER', list),
        'SOURCE OBSERVER IDS': ('OBSERVER ID', list),
    }).reset_index()
    representative = representative.merge(provenance, on='EVENT ID', validate='one_to_one')
    observations = ebd.sort_values('SAMPLING EVENT IDENTIFIER', kind='stable').drop_duplicates(['EVENT ID', 'TAXON CONCEPT ID']).copy()
    observations = observations.rename(columns={
        'SAMPLING EVENT IDENTIFIER': 'ORIGINAL SAMPLING EVENT IDENTIFIER', 'OBSERVER ID': 'ORIGINAL OBSERVER ID',
    }).drop(columns=EVENT_METADATA)
    observations = observations.merge(representative.drop(columns='GROUP IDENTIFIER'), on='EVENT ID', validate='many_to_one')
    return observations.sort_values('OBSERVATION DATETIME', kind='stable').reset_index(drop=True), members


def qualifies_effort(chk):
    """Complete accepted checklists with known timing and spatial support."""
    return (chk['KEEP PENTAD'] & chk['KEEP PROTOCOL'] & chk['ALL SPECIES REPORTED'].eq(1)
            & chk['DURATION MINUTES'].gt(0) & chk['OBSERVATION DATETIME'].notna()
            & ~chk['SHARED METADATA CONFLICT'])


def effort_by_day(chk, keys):
    """Union eligible time intervals, split at midnight, then sum per day.

    Independent of row order; concurrent lists from one analysis unit cannot
    manufacture extra hours. Unknown starts never become midnight observations.
    """
    rows = []
    for key, group in chk.loc[qualifies_effort(chk)].groupby(keys, sort=False):
        key = key if isinstance(key, tuple) else (key,)
        intervals = []
        for start, duration in group[['OBSERVATION DATETIME', 'DURATION MINUTES']].sort_values('OBSERVATION DATETIME').itertuples(index=False, name=None):
            end = start + pd.Timedelta(minutes=duration)
            if intervals and start <= intervals[-1][1]:
                intervals[-1][1] = max(intervals[-1][1], end)
            else:
                intervals.append([start, end])
        for start, end in intervals:
            while start < end:
                stop = min(end, start.normalize() + pd.Timedelta(days=1))
                rows.append((*key, start.normalize(), (stop - start).total_seconds() / 60))
                start = stop
    daily = pd.DataFrame(rows, columns=[*keys, 'OBSERVATION DATE', 'DURATION MINUTES'])
    daily['OBSERVATION DATE'] = pd.to_datetime(daily['OBSERVATION DATE'])
    return daily.groupby([*keys, 'OBSERVATION DATE'], as_index=False)['DURATION MINUTES'].sum()


def cross_pentad_overlaps(chk):
    """Flag contradictory same-observer timing across cells, without allocating it.

    Adjacent intervals are not overlaps. The flag is diagnostic: no evidence
    identifies which reported location or interval should be changed.
    """
    conflict = pd.Series(False, index=chk.index)
    for _, group in chk.loc[qualifies_effort(chk)].groupby('OBSERVER ID', sort=False):
        active = []
        for index, start, duration, pentad in group.sort_values('OBSERVATION DATETIME').reset_index()[
            ['index', 'OBSERVATION DATETIME', 'DURATION MINUTES', 'PENTAD']
        ].itertuples(index=False, name=None):
            active = [row for row in active if row[1] > start]
            for previous, _, previous_pentad in active:
                if pentad != previous_pentad:
                    conflict.loc[[index, previous]] = True
            active.append((index, start + pd.Timedelta(minutes=duration), pentad))
    return conflict
