"""Strict taxonomy matching, feedback, and version/checksum regressions."""

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import requests

from eBird2ABAP.taxonomy import (TaxonomyMatchError, add_avilist_taxonomy,
    build_crosswalk, check_taxonomy_updates, load_taxonomy_bundle, update_taxonomy)


def references():
    av = pd.DataFrame({
        'RANK': ['species'], 'AVIBASE ID': ['avibase-12345678'],
        'SPECIES CODE CORNELL LAB': ['bird1'], 'ENGLISH NAME: AVILIST': ['Current Bird'],
        'SCIENTIFIC NAME': ['Current bird'], 'ORDER': ['Order'], 'FAMILY': ['Family'], '#': [1],
        'ENGLISH NAME: CLEMENTS v2026': ['Bird'],
    })
    source = [{'speciesCode': 'bird1', 'sciName': 'Oldgenus bird', 'category': 'species'}]
    target = [{'speciesCode': 'bird1', 'sciName': 'Current bird', 'category': 'species'}]
    return av, source, target


class TaxonomyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        mapping, av = build_crosswalk(*references())
        payloads = {'ebird_avilist_mapping.csv': mapping.to_csv(index=False).encode(),
                    'avilist_reference.csv': av.to_csv(index=False).encode()}
        for name, data in payloads.items():
            (self.root / name).write_bytes(data)
        manifest = {'ebird_source_version': '2025', 'ebird_target_version': '2026', 'avilist_version': '2026',
                    'files': {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()}}
        (self.root / 'taxonomy_manifest.json').write_text(json.dumps(manifest))
        self.ebd = pd.DataFrame({'SCIENTIFIC NAME': ['Oldgenus bird'], 'CATEGORY': ['species'],
                                 'TAXON CONCEPT ID': ['avibase-12345678']})

    def match(self, frame=None, **kwargs):
        return add_avilist_taxonomy(self.ebd if frame is None else frame, ebird_version='2025',
                                    taxonomy_dir=self.root, **kwargs)

    def test_direct_concept_and_published_code_allow_changed_names(self):
        row = self.match().iloc[0]
        self.assertEqual(row['AVILIST MATCH'], 'exact')
        self.assertEqual(row['AVIBASE ID'], 'avibase-12345678')
        self.assertEqual(row['AVILIST SCIENTIFIC NAME'], 'Current bird')
        self.assertEqual(row['AVILIST COMMON NAME'], 'Current Bird')

    def test_same_scientific_name_with_different_concept_never_matches(self):
        self.ebd['TAXON CONCEPT ID'] = 'avibase-87654321'
        with self.assertRaises(TaxonomyMatchError) as error:
            self.match(report_dir=self.root / 'report')
        self.assertEqual(error.exception.report.iloc[0]['AVILIST MATCH'], 'concept_id_mismatch')
        self.assertTrue((self.root / 'report/summary.json').exists())
        with self.assertWarns(UserWarning):
            result = self.match(strict=False)
        self.assertEqual(result.iloc[0]['AVIBASE ID'], 'avibase-87654321')
        self.assertTrue(pd.isna(result.iloc[0]['AVILIST COMMON NAME']))

    def test_unknown_name_has_no_name_or_id_fallback(self):
        self.ebd['SCIENTIFIC NAME'] = 'Unknown bird'
        report = self.match(return_unmatched=True)
        self.assertEqual(report.iloc[0]['AVILIST MATCH'], 'source_name_category_not_found')

    def test_subspecies_are_not_replaced_with_parent_concepts(self):
        self.ebd['CATEGORY'] = 'issf'
        self.ebd['TAXON CONCEPT ID'] = 'avibase-87654321'
        with self.assertWarns(UserWarning):
            row = self.match(strict=False).iloc[0]
        self.assertEqual(row['AVIBASE ID'], 'avibase-87654321')
        self.assertNotEqual(row['AVILIST MATCH'], 'exact')
        self.assertTrue(pd.isna(row['AVILIST SCIENTIFIC NAME']))

    def test_source_version_is_required_and_cannot_be_relabelled(self):
        for version in [None, '2026']:
            with self.subTest(version=version), self.assertRaisesRegex(ValueError, 'Declare ebird_version'):
                add_avilist_taxonomy(self.ebd, ebird_version=version, taxonomy_dir=self.root)

    def test_missing_id_is_not_resolved_by_its_name(self):
        self.ebd['TAXON CONCEPT ID'] = None
        with self.assertRaises(TaxonomyMatchError) as error:
            self.match()
        self.assertEqual(error.exception.report.iloc[0]['AVILIST MATCH'], 'missing_concept_id')

    def test_bundle_checksum_rejects_stale_or_mixed_references(self):
        with (self.root / 'ebird_avilist_mapping.csv').open('a') as stream:
            stream.write('\n')
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            self.match()

    def test_no_legacy_file_fallback_when_manifest_missing(self):
        (self.root / 'taxonomy_manifest.json').unlink()
        (self.root / 'matched_species.csv').write_text('SCIENTIFIC NAME,ADU\nOldgenus bird,123\n')
        with self.assertRaises(FileNotFoundError):
            self.match()

    def test_ambiguous_published_links_or_ids_reject_update(self):
        av, source, target = references()
        for column, value in [('AVIBASE ID', 'avibase-87654321'), ('SPECIES CODE CORNELL LAB', 'bird2')]:
            duplicated = pd.concat([av, av], ignore_index=True)
            duplicated.loc[1, column] = value
            with self.subTest(column=column), self.assertRaises(ValueError):
                build_crosswalk(duplicated, source, target)

    def test_no_published_link_remains_unresolved(self):
        av, source, target = references()
        av['SPECIES CODE CORNELL LAB'] = None
        mapping, _ = build_crosswalk(av, source, target)
        self.assertEqual(mapping.iloc[0]['REFERENCE STATUS'], 'no_published_avilist_link')

    def test_failed_network_update_preserves_the_active_bundle(self):
        original = (self.root / 'taxonomy_manifest.json').read_bytes()
        with patch('eBird2ABAP.taxonomy.latest_ebird_version', side_effect=requests.HTTPError('offline')):
            with self.assertRaises(requests.HTTPError):
                update_taxonomy('unused.xlsx', ebird_version='2025', avilist_version='2026', output_dir=self.root)
        self.assertEqual((self.root / 'taxonomy_manifest.json').read_bytes(), original)
        load_taxonomy_bundle(self.root)

    def test_update_check_failure_is_not_reported_as_up_to_date(self):
        with patch('eBird2ABAP.taxonomy.current_taxonomy_versions', side_effect=requests.HTTPError('403')):
            with self.assertRaises(requests.HTTPError):
                check_taxonomy_updates(self.root)

    def test_empty_input_is_an_empty_audit(self):
        self.assertTrue(self.match(self.ebd.iloc[:0], return_unmatched=True).empty)


if __name__ == '__main__':
    unittest.main()
