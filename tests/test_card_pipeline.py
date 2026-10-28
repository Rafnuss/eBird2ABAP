"""Offline regression tests using synthetic observations, never private EBD data."""

import gzip
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd

from eBird2ABAP.taxonomy import TaxonomyMatchError

from eBird2ABAP.ebird2card import (
    add_avilist_taxonomy, checkday_pentad_observer, chk2valid_card,
    download_EBD, ebd2chk, ebird2abap, read_EBD,
)


def observations(durations=(60, 60), dates=("2026-01-01", "2026-01-05")):
    """Two checklists at a southern/eastern pentad centre."""
    return pd.DataFrame({
        "SAMPLING EVENT IDENTIFIER": [f"S{i}" for i in range(len(durations))],
        "GROUP IDENTIFIER": np.nan,
        "SCIENTIFIC NAME": "Apteryx australis",
        "TAXON CONCEPT ID": "avibase-6BA55EF0",
        "CATEGORY": "species",
        "LATITUDE": -25.0416666667,
        "LONGITUDE": 27.0416666667,
        "OBSERVATION DATE": list(dates),
        "TIME OBSERVATIONS STARTED": "06:00:00",
        "PROTOCOL TYPE": "Stationary",
        "DURATION MINUTES": list(durations),
        "EFFORT DISTANCE KM": 0.0,
        "ALL SPECIES REPORTED": 1,
        "OBSERVER ID": "obs1",
    })


class CardPipelineTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.input = self.root / "observations.txt"

    def write_input(self, frame):
        frame.to_csv(self.input, sep="\t", index=False)
        return self.input

    def convert(self, frame, **kwargs):
        return ebird2abap(self.write_input(frame), self.root / "exports/cards.json", ebird_version="2025", **kwargs)

    def test_end_to_end_exports_and_observer_configuration(self):
        cards = self.convert(observations(), exportCSV=True,
                             observer_email="research@example.org", observer_no="123")
        exported = json.loads((self.root / "exports/cards.json").read_text())
        self.assertEqual(len(cards), 1)
        card = exported[0]
        self.assertEqual(card["TotalHours"], 2)
        self.assertEqual(card["TotalSpp"], 1)
        self.assertEqual(card["Checklists"], ["S0", "S1"])
        self.assertEqual(card["SourceChecklists"], ["S0", "S1"])
        self.assertEqual(card["SourceObservers"], ["obs1"])
        self.assertEqual(card["ValidationStatus"], "candidate")
        self.assertIsNone(card["records"][0]["Sequence"])
        self.assertEqual(card["records"][0]["RecordIndex"], 1)
        self.assertEqual(card["ObserverEmail"], "research@example.org")
        self.assertEqual(card["ObserverNo"], "123")
        self.assertIsNone(card["records"][0]["Accuracy"])
        self.assertEqual(card["records"][0]["SightingTime"], "2026-01-01T06:00:00")
        self.assertEqual(len(pd.read_csv(self.root / "exports/cards_cards.csv")), 1)
        self.assertEqual(len(pd.read_csv(self.root / "exports/cards_records.csv")), 1)

    def test_no_cards_and_empty_input_write_empty_json(self):
        for frame in [observations((20,), ("2026-01-01",)), observations().iloc[:0],
                      observations((60, 60), ("2026-01-01", "2026-01-06"))]:
            with self.subTest(rows=len(frame)):
                self.assertTrue(self.convert(frame, exportCSV=True).empty)
                self.assertEqual(json.loads((self.root / "exports/cards.json").read_text()), [])

    def test_failed_window_does_not_skip_later_valid_window(self):
        cards = self.convert(observations((10, 60, 60), ("2026-01-01", "2026-01-05", "2026-01-06")))
        self.assertEqual(cards.iloc[0]["StartDate"], "2026-01-05")
        self.assertEqual(cards.iloc[0]["Checklists"], ["S1", "S2"])

    def test_successful_windows_do_not_overlap(self):
        cards = self.convert(observations((120, 120, 120), ("2026-01-01", "2026-01-05", "2026-01-06")))
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards["TotalHours"].tolist(), [4, 2])

    def test_unmatched_taxa_require_a_report_and_explicit_permissive_mode(self):
        frame = observations()
        frame.loc[1, "SCIENTIFIC NAME"] = "Unresolved bird"
        frame.loc[1, "TAXON CONCEPT ID"] = "avibase-00000000"
        with self.assertRaises(TaxonomyMatchError):
            self.convert(frame)
        self.assertFalse((self.root / "exports/cards.json").exists())
        self.assertTrue((self.root / "exports/cards_taxonomy/unresolved_taxa.csv").exists())
        with self.assertWarnsRegex(UserWarning, "Retaining 1 unresolved"):
            cards = self.convert(frame, strict_taxonomy=False)
        self.assertEqual(cards.iloc[0]["TotalSpp"], 2)
        self.assertEqual(cards.iloc[0]["TotalHours"], 2)
        unresolved = next(record for record in cards.iloc[0]["records"] if record["Spp"] == "avibase-00000000")
        self.assertTrue(pd.isna(unresolved["ScientificName"]))
        self.assertEqual(unresolved["TaxonomyStatus"], "source_name_category_not_found")
        exported = json.loads((self.root / "exports/cards.json").read_text())
        record = next(row for row in exported[0]["records"] if row["Spp"] == "avibase-00000000")
        self.assertIsNone(record["CommonName"])
        self.assertEqual(record["AviListVersion"], "2026")

    def test_missing_distance_accuracy_is_blank(self):
        frame = observations()
        frame["EFFORT DISTANCE KM"] = np.nan
        cards = self.convert(frame)
        self.assertIsNone(cards.iloc[0]["records"][0]["Accuracy"])

    def test_protocol_completeness_and_spatial_rules(self):
        for column, value in [("ALL SPECIES REPORTED", 0), ("PROTOCOL TYPE", "Other"),
                              ("EFFORT DISTANCE KM", 100), ("DURATION MINUTES", 0)]:
            frame = observations()
            frame[column] = value
            chk = ebd2chk(read_EBD(self.write_input(frame)))
            with self.subTest(column=column):
                self.assertTrue(chk2valid_card(chk).empty)
        frame = observations()
        frame["PROTOCOL TYPE"] = "Historical"
        frame["EFFORT DISTANCE KM"] = np.nan
        self.assertFalse(ebd2chk(read_EBD(self.write_input(frame)))["KEEP PENTAD"].any())

    def test_observer_and_pentad_effort_are_separate(self):
        for column, value in [("OBSERVER ID", "obs2"), ("LONGITUDE", 28.0416666667)]:
            frame = observations()
            frame.loc[1, column] = value
            with self.subTest(column=column):
                self.assertTrue(self.convert(frame).empty)

    def test_card_effort_validation_in_every_quadrant(self):
        for lat, lng in [(0.0416666667, 10.0416666667), (4.375, -7.375),
                         (-15.875, -5.625), (-25.0416666667, 27.0416666667)]:
            frame = observations()
            frame["LATITUDE"] = lat
            frame["LONGITUDE"] = lng
            with self.subTest(lat=lat, lng=lng):
                cards = self.convert(frame)
                self.assertEqual(len(cards), 1)
                self.assertEqual(cards.iloc[0]["TotalHours"], 2)

    def test_project_protocol_gzip_directory_and_nrows(self):
        frame = observations().rename(columns={"PROTOCOL TYPE": "PROTOCOL NAME"})
        path = self.root / "project-report.txt.gz"
        with gzip.open(path, "wt") as stream:
            frame.to_csv(stream, sep="\t", index=False)
        (self.root / "project-sampling-report.txt").write_text("metadata\n")
        loaded = read_EBD(self.root, nrows=1)
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded.iloc[0]["PROTOCOL TYPE"], "Stationary")
        self.write_input(observations())
        with self.assertRaisesRegex(ValueError, "More than one"):
            read_EBD(self.root)

    def test_shared_checklists_do_not_double_count_effort(self):
        frame = observations((120, 120), ("2026-01-01", "2026-01-01"))
        frame["GROUP IDENTIFIER"] = "G1"
        cards = self.convert(frame)
        self.assertEqual(cards.iloc[0]["TotalHours"], 2)
        self.assertEqual(cards.iloc[0]["Checklists"], ["S0"])

    def test_empty_taxonomy_diagnostic(self):
        self.assertTrue(add_avilist_taxonomy(observations().iloc[:0], return_unmatched=True).empty)

    def test_window_selection_matches_simple_reference(self):
        rng = np.random.default_rng(42)
        for _ in range(30):
            dates = pd.Timestamp("2026-01-01") + pd.to_timedelta(np.sort(rng.choice(200, 50, replace=False)), unit="D")
            durations = rng.integers(1, 120, 50)
            frame = pd.DataFrame({"OBSERVATION DATE": dates, "DURATION MINUTES": durations,
                                  "pentad_observer_date": [f"C{i}" for i in range(50)]})
            expected = [""] * 50
            start = 0
            while start < 50:
                end = start + 1
                while end < 50 and dates[end] - dates[start] < pd.Timedelta(days=5):
                    end += 1
                if sum(durations[start:end]) >= 120:
                    expected[start:end] = [f"C{start}"] * (end - start)
                    start = end
                else:
                    start += 1
            self.assertEqual(checkday_pentad_observer(frame)["CARD"].tolist(), expected)


class DownloadTests(unittest.TestCase):
    @patch("eBird2ABAP.ebird2card.requests.get")
    def test_archive_cannot_escape_output_directory(self, get):
        archive = io.BytesIO()
        with tarfile.open(fileobj=archive, mode="w") as stream:
            member = tarfile.TarInfo("../../escape.txt")
            member.size = 4
            stream.addfile(member, io.BytesIO(b"test"))
        response = Mock(status_code=200, headers={})
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [archive.getvalue()]
        get.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(tarfile.OutsideDestinationError):
                download_EBD("2026", "Jan", directory)
            self.assertFalse((Path(directory) / "escape.txt").exists())
        self.assertEqual(get.call_args.kwargs["timeout"], (30, 120))

    @patch("eBird2ABAP.ebird2card.requests.get")
    def test_explicit_release_does_not_fall_back(self, get):
        import requests
        response = Mock(status_code=404)
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.raise_for_status.side_effect = requests.HTTPError("404")
        get.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(requests.HTTPError):
                download_EBD("2026", "Jan", directory)
        self.assertEqual(get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
