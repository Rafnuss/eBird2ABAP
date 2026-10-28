"""Card-window regressions independent of taxonomy and export schema."""

import unittest

import numpy as np
import pandas as pd

from eBird2ABAP.ebird2card import checkday_pentad_observer, chk2valid_card


def checklists(durations, dates):
    return pd.DataFrame({
        'PENTAD': ['2500_2700'] * len(durations),
        'OBSERVER ID': ['obs1'] * len(durations),
        'OBSERVATION DATE': pd.to_datetime(dates),
        'OBSERVATION DATETIME': pd.to_datetime(dates) + pd.Timedelta(hours=6),
        'SHARED METADATA CONFLICT': False,
        'DURATION MINUTES': durations,
        'KEEP PENTAD': True,
        'KEEP PROTOCOL': True,
        'ALL SPECIES REPORTED': 1,
    })


class CardSelectionTests(unittest.TestCase):
    def test_failed_window_does_not_skip_a_later_valid_start(self):
        chk = checklists([10, 60, 60], ['2026-01-01', '2026-01-05', '2026-01-06'])
        cards = chk2valid_card(chk)
        self.assertEqual(cards['OBSERVATION DATE'].tolist(), [pd.Timestamp('2026-01-05')])

    def test_exactly_two_hours_qualifies(self):
        self.assertEqual(len(chk2valid_card(checklists([120], ['2026-01-01']))), 1)
        self.assertEqual(len(chk2valid_card(checklists([60, 60], ['2026-01-01', '2026-01-05']))), 1)

    def test_sixth_calendar_day_is_outside_the_window(self):
        self.assertTrue(chk2valid_card(checklists([60, 60], ['2026-01-01', '2026-01-06'])).empty)

    def test_successful_windows_remain_non_overlapping(self):
        chk = checklists([120, 120, 120], ['2026-01-01', '2026-01-05', '2026-01-06'])
        self.assertEqual(chk2valid_card(chk)['OBSERVATION DATE'].tolist(),
                         [pd.Timestamp('2026-01-01'), pd.Timestamp('2026-01-06')])

    def test_no_qualifying_effort_returns_a_typed_empty_card_table(self):
        short = checklists([20], ['2026-01-01'])
        incomplete = checklists([120], ['2026-01-01'])
        incomplete['ALL SPECIES REPORTED'] = 0
        for chk in [short, incomplete, short.iloc[:0]]:
            with self.subTest(rows=len(chk), minutes=chk['DURATION MINUTES'].sum()):
                cards = chk2valid_card(chk)
                self.assertTrue(cards.empty)
                self.assertEqual(cards.columns.tolist(), ['PENTAD', 'OBSERVER ID', 'OBSERVATION DATE', 'CARD'])
                self.assertTrue(pd.api.types.is_datetime64_any_dtype(cards['OBSERVATION DATE']))

    def test_eligibility_flags_are_respected(self):
        for column, value in [('KEEP PENTAD', False), ('KEEP PROTOCOL', False),
                              ('DURATION MINUTES', 0), ('ALL SPECIES REPORTED', 0)]:
            chk = checklists([120], ['2026-01-01'])
            chk[column] = value
            with self.subTest(column=column):
                self.assertTrue(chk2valid_card(chk).empty)

    def test_observers_and_pentads_cannot_pool_effort(self):
        for column, value in [('OBSERVER ID', 'obs2'), ('PENTAD', '2500_2800')]:
            chk = checklists([60, 60], ['2026-01-01', '2026-01-02'])
            chk.loc[1, column] = value
            with self.subTest(column=column):
                self.assertTrue(chk2valid_card(chk).empty)

    def test_date_windows_match_an_independent_reference(self):
        rng = np.random.default_rng(42)
        for _ in range(30):
            dates = pd.Timestamp('2026-01-01') + pd.to_timedelta(np.sort(rng.choice(200, 50, replace=False)), unit='D')
            durations = rng.integers(1, 120, 50)
            frame = pd.DataFrame({'OBSERVATION DATE': dates, 'DURATION MINUTES': durations,
                                  'pentad_observer_date': [f'C{i}' for i in range(50)]})
            expected = [''] * 50
            start = 0
            while start < 50:
                end = start + 1
                while end < 50 and dates[end] - dates[start] < pd.Timedelta(days=5):
                    end += 1
                if sum(durations[start:end]) >= 120:
                    expected[start:end] = [f'C{start}'] * (end - start)
                    start = end
                else:
                    start += 1
            self.assertEqual(checkday_pentad_observer(frame)['CARD'].tolist(), expected)


if __name__ == '__main__':
    unittest.main()
