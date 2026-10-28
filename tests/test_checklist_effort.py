"""Independent-event and elapsed-effort scientific policy regressions."""

from pathlib import Path
import tempfile
import unittest

import numpy as np
import pandas as pd

from eBird2ABAP import (read_EBD, ebd2chk, chk2valid_card, valid_card2chk_card, chk_card2card_chk)


def source_rows(starts=('06:00:00', '07:00:00'), durations=(60, 60)):
    return pd.DataFrame({
        'SAMPLING EVENT IDENTIFIER': [f'S{i}' for i in range(len(starts))],
        'GROUP IDENTIFIER': None, 'OBSERVER ID': 'obs1', 'CATEGORY': 'species',
        'SCIENTIFIC NAME': 'Struthio camelus', 'TAXON CONCEPT ID': 'avibase-2247CB05',
        'LATITUDE': -25 - 1/24, 'LONGITUDE': 27 + 1/24, 'OBSERVATION DATE': '2026-01-01',
        'TIME OBSERVATIONS STARTED': list(starts), 'DURATION MINUTES': list(durations),
        'EFFORT DISTANCE KM': 0.0, 'ALL SPECIES REPORTED': 1, 'PROTOCOL TYPE': 'Stationary',
    })


class ChecklistEffortTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.file = self.root / 'ebd.txt'

    def read(self, frame):
        frame.to_csv(self.file, sep='\t', index=False)
        return read_EBD(self.file)

    def metadata(self, frame):
        chk = ebd2chk(self.read(frame))
        cards = chk2valid_card(chk)
        return chk_card2card_chk(valid_card2chk_card(chk, cards), cards)

    def test_shared_union_preserves_concepts_members_and_input_order_independence(self):
        frame = source_rows(('06:00:00',) * 3, (120,) * 3)
        frame['GROUP IDENTIFIER'] = 'G1'
        frame['OBSERVER ID'] = ['obs1', 'obs2', 'obs3']
        frame.loc[2, 'TAXON CONCEPT ID'] = 'avibase-40329BB6'
        first = self.read(frame)
        second = self.read(frame.iloc[::-1])
        self.assertEqual(len(first), 2)
        self.assertEqual(first['TAXON CONCEPT ID'].tolist(), second['TAXON CONCEPT ID'].tolist())
        self.assertEqual(first.iloc[0]['EVENT ID'], 'G1')
        self.assertEqual(first.iloc[0]['SOURCE CHECKLIST IDS'], ['S0', 'S1', 'S2'])
        self.assertEqual(first.iloc[0]['SOURCE OBSERVER IDS'], ['obs1', 'obs2', 'obs3'])
        self.assertEqual(first['SAMPLING EVENT IDENTIFIER'].unique().tolist(), ['S0'])
        self.assertEqual(self.metadata(frame).iloc[0]['DURATION MINUTES_sum'], 120)

    def test_conflicting_shared_metadata_is_flagged_and_cannot_establish_effort(self):
        frame = source_rows(('06:00:00', '06:00:00'), (120, 180))
        frame['GROUP IDENTIFIER'] = 'G1'
        chk = ebd2chk(self.read(frame))
        self.assertTrue(chk['SHARED METADATA CONFLICT'].all())
        self.assertTrue(chk2valid_card(chk).empty)

    def test_overlapping_hour_lists_do_not_make_two_hours(self):
        chk = ebd2chk(self.read(source_rows(('06:00:00', '06:30:00'))))
        self.assertTrue(chk2valid_card(chk).empty)
        frame = source_rows(('06:00:00', '06:30:00'), (90, 90))
        frame['EFFORT DISTANCE KM'] = 0.01
        metadata = self.metadata(frame)
        self.assertEqual(metadata.iloc[0]['DURATION MINUTES_sum'], 120)
        self.assertEqual(metadata.iloc[0]['OVERLAP MINUTES REMOVED'], 60)
        self.assertTrue(pd.isna(metadata.iloc[0]['EFFORT DISTANCE KM_sum']))

    def test_known_zero_distances_remain_zero_even_with_timer_overlap(self):
        metadata = self.metadata(source_rows(('06:00:00', '06:30:00'), (90, 90)))
        self.assertEqual(metadata.iloc[0]['EFFORT DISTANCE KM_sum'], 0)

    def test_missing_start_is_unknown_and_cannot_qualify(self):
        chk = ebd2chk(self.read(source_rows((None,), (120,))))
        self.assertTrue(chk['OBSERVATION DATETIME'].isna().all())
        self.assertTrue(chk2valid_card(chk).empty)

    def test_missing_distance_stays_missing_even_when_stationary_spatial_screen_passes(self):
        frame = source_rows()
        frame['EFFORT DISTANCE KM'] = np.nan
        metadata = self.metadata(frame)
        self.assertTrue(pd.isna(metadata.iloc[0]['EFFORT DISTANCE KM_sum']))
        frame['PROTOCOL TYPE'] = 'Traveling'
        chk = ebd2chk(self.read(frame))
        self.assertEqual(chk['SPATIAL STATUS'].unique().tolist(), ['unknown_distance'])
        self.assertTrue(chk2valid_card(chk).empty)

    def test_incomplete_and_incidental_supplements_do_not_increase_effort(self):
        frame = source_rows(('06:00:00', '09:00:00', '10:00:00'), (120, 300, 300))
        frame.loc[1, 'ALL SPECIES REPORTED'] = 0
        frame.loc[2, 'PROTOCOL TYPE'] = 'Incidental'
        metadata = self.metadata(frame)
        self.assertEqual(len(metadata.iloc[0]['SAMPLING EVENT IDENTIFIER_list']), 3)
        self.assertEqual(metadata.iloc[0]['DURATION MINUTES_sum'], 120)

    def test_date_fields_with_embedded_noon_are_normalized_to_calendar_days(self):
        frame = source_rows(('06:00:00',), (120,))
        frame['OBSERVATION DATE'] = '2026-01-01 12:00:00'
        observations = self.read(frame)
        self.assertEqual(observations.iloc[0]['OBSERVATION DATE'], pd.Timestamp('2026-01-01'))
        self.assertEqual(len(chk2valid_card(ebd2chk(observations))), 1)

    def test_midnight_end_and_five_day_clipping(self):
        metadata = self.metadata(source_rows(('23:00:00',), (120,)))
        self.assertEqual(metadata.iloc[0]['OBSERVATION DATETIME_max'], pd.Timestamp('2026-01-02 01:00'))
        frame = source_rows(('06:00:00', '23:00:00'), (120, 120))
        frame.loc[1, 'OBSERVATION DATE'] = '2026-01-05'
        metadata = self.metadata(frame)
        self.assertEqual(metadata.iloc[0]['DURATION MINUTES_sum'], 180)
        self.assertLess(metadata.iloc[0]['OBSERVATION DATETIME_max'], pd.Timestamp('2026-01-06'))

    def test_stationary_boundary_screen_has_no_overlap_allowance(self):
        frame = source_rows(('06:00:00',), (120,))
        frame['LONGITUDE'] = 27.00001
        chk = ebd2chk(self.read(frame))
        self.assertEqual(chk.iloc[0]['SPATIAL STATUS'], 'possible_boundary_crossing')
        self.assertFalse(chk.iloc[0]['KEEP PENTAD'])

    def test_cross_pentad_overlaps_are_flagged_without_guessing_an_allocation(self):
        frame = source_rows(('06:00:00', '06:30:00', '08:00:00'), (60, 60, 60))
        frame.loc[1, 'LONGITUDE'] = 28 + 1/24
        chk = ebd2chk(self.read(frame))
        self.assertEqual(chk['CROSS PENTAD TIME CONFLICT'].tolist(), [True, True, False])
        self.assertEqual(chk['DURATION MINUTES'].tolist(), [60, 60, 60])




if __name__ == '__main__':
    unittest.main()
