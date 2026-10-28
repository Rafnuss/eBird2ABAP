"""Explicit, versioned EBD → eBird → AviList matching without ADU or fallback."""

import hashlib
from datetime import datetime, timezone
import importlib.resources as resources
import json
from pathlib import Path
import re
import shutil
import warnings

import pandas as pd
import requests

PACKAGE_DIR = Path(__file__).parent
EBIRD_API = 'https://api.ebird.org/v2/ref/taxonomy'
AVILIST_SITE = 'https://www.avilist.org/'


class TaxonomyMatchError(ValueError):
    """Conversion stopped; report and summary remain available for inspection."""

    def __init__(self, report, summary):
        self.report = report
        self.summary = summary
        super().__init__(f"Taxonomy unresolved for {summary['unmatched_observations']} observations; inspect the taxonomy report. No fallback was applied.")


def latest_ebird_version():
    response = requests.get(f'{EBIRD_API}/versions', timeout=(30, 120))
    response.raise_for_status()
    latest = [format(row['authorityVer'], 'g') for row in response.json() if row['latest']]
    if len(latest) != 1:
        raise ValueError('eBird must identify exactly one latest taxonomy version')
    return latest[0]


def current_taxonomy_versions():
    """Check published releases; an unavailable website never means up to date."""
    latest = latest_ebird_version()
    response = requests.get(AVILIST_SITE, timeout=(30, 120))
    response.raise_for_status()
    versions = re.findall(r'/checklist/v(\d{4}[a-z]?)/', response.text)
    if not versions:
        raise ValueError('Cannot establish the latest AviList release from its official site')
    return {'ebird_target_version': latest, 'avilist_version': max(versions)}


def fetch_ebird_taxonomy(version):
    response = requests.get(f'{EBIRD_API}/ebird', params={'fmt': 'json', 'version': version}, timeout=(30, 120))
    response.raise_for_status()
    return response.json()


def build_crosswalk(avilist, source, target):
    """Use only AviList's published species-code link; no name matching to AviList."""
    av = avilist.loc[avilist['RANK'].eq('species'), [
        'AVIBASE ID', 'SPECIES CODE CORNELL LAB', 'ENGLISH NAME: AVILIST',
        'SCIENTIFIC NAME', 'ORDER', 'FAMILY', '#',
    ]].rename(columns={
        'SPECIES CODE CORNELL LAB': 'EBIRD SPECIES CODE',
        'ENGLISH NAME: AVILIST': 'AVILIST COMMON NAME',
        'SCIENTIFIC NAME': 'AVILIST SCIENTIFIC NAME',
        'ORDER': 'AVILIST ORDER', 'FAMILY': 'AVILIST FAMILY', '#': 'AVILIST SEQUENCE',
        'AVIBASE ID': 'EXPECTED AVIBASE ID',
    })
    if av['EXPECTED AVIBASE ID'].isna().any() or av['EXPECTED AVIBASE ID'].duplicated().any():
        raise ValueError('AviList species need unique non-missing Avibase IDs; update rejected: ' + str(av.loc[av['EXPECTED AVIBASE ID'].isna() | av['EXPECTED AVIBASE ID'].duplicated(keep=False)].to_dict('records')[:10]))
    links = av.dropna(subset=['EBIRD SPECIES CODE'])
    if links['EBIRD SPECIES CODE'].duplicated().any():
        raise ValueError('Ambiguous AviList species-code links; update rejected: ' + str(links.loc[links['EBIRD SPECIES CODE'].duplicated(keep=False), ['EBIRD SPECIES CODE', 'EXPECTED AVIBASE ID']].to_dict('records')))
    src = pd.DataFrame(source)[['speciesCode', 'sciName', 'category']].rename(columns={
        'speciesCode': 'EBIRD SPECIES CODE', 'sciName': 'EBIRD SCIENTIFIC NAME', 'category': 'EBIRD CATEGORY',
    })
    if src[['EBIRD SCIENTIFIC NAME', 'EBIRD CATEGORY']].duplicated().any() or src['EBIRD SPECIES CODE'].duplicated().any():
        raise ValueError('Ambiguous eBird source keys; reference update rejected')
    dst = pd.DataFrame(target)[['speciesCode', 'category']].rename(columns={
        'speciesCode': 'EBIRD SPECIES CODE', 'category': 'TARGET EBIRD CATEGORY',
    })
    mapping = src.merge(links, on='EBIRD SPECIES CODE', how='left', validate='one_to_one')
    mapping = mapping.merge(dst, on='EBIRD SPECIES CODE', how='left', validate='one_to_one')
    mapping['REFERENCE STATUS'] = 'linked'
    mapping.loc[mapping['EXPECTED AVIBASE ID'].isna(), 'REFERENCE STATUS'] = 'no_published_avilist_link'
    mapping.loc[mapping['TARGET EBIRD CATEGORY'].isna(), 'REFERENCE STATUS'] = 'code_absent_from_target_ebird'
    mapping.loc[mapping['TARGET EBIRD CATEGORY'].notna() & mapping['TARGET EBIRD CATEGORY'].ne('species'), 'REFERENCE STATUS'] = 'target_ebird_not_species'
    mapping.loc[mapping['EBIRD CATEGORY'].ne('species'), 'REFERENCE STATUS'] = 'source_ebird_not_species'
    return mapping, av


def update_taxonomy(avilist_file, *, ebird_version, avilist_version, output_dir=None, source_dir=None):
    """Activate one current bundle from an explicit source EBD release and latest target.

    The workbook version is explicitly declared; its Clements crosswalk must
    target the current eBird release. An explicit website check is separate,
    since website availability must not be mistaken for taxonomic validity.
    """
    versions = {'ebird_target_version': latest_ebird_version(), 'avilist_version': str(avilist_version)}
    avilist_file = Path(avilist_file)
    sheet = f"AviList v{versions['avilist_version']}"
    avilist = pd.read_excel(avilist_file, sheet_name=sheet)
    if f"ENGLISH NAME: CLEMENTS v{versions['ebird_target_version']}" not in avilist.columns:
        raise ValueError('The supplied AviList does not declare a crosswalk to the latest eBird/Clements release; update rejected')
    citation = pd.read_excel(avilist_file, sheet_name='Recommended citation', header=None).iloc[:, 0].dropna().tolist()
    source = fetch_ebird_taxonomy(str(ebird_version))
    target = source if str(ebird_version) == versions['ebird_target_version'] else fetch_ebird_taxonomy(versions['ebird_target_version'])
    mapping, av = build_crosswalk(avilist, source, target)
    payloads = {
        'ebird_avilist_mapping.csv': mapping.to_csv(index=False).encode(),
        'avilist_reference.csv': av.to_csv(index=False).encode(),
    }
    manifest = {
        'schema_version': 1, 'updated_at_utc': datetime.now(timezone.utc).isoformat(), 'ebird_source_version': str(ebird_version), **versions,
        'avilist_file': avilist_file.name,
        'avilist_sha256': hashlib.sha256(avilist_file.read_bytes()).hexdigest(),
        'avilist_sheet': sheet, 'avilist_selection': 'explicit workbook/version; freshness requires a successful separate website check', 'avilist_url': f"{AVILIST_SITE}checklist/v{versions['avilist_version']}/",
        'avilist_citation': citation[0],
        'avilist_license_statement': next(text for text in citation if 'licensed under' in text),
        'ebird_api': EBIRD_API,
        'source_api_sha256': hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest(),
        'target_api_sha256': hashlib.sha256(json.dumps(target, sort_keys=True).encode()).hexdigest(),
        'files': {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
        'source_taxa': len(mapping), 'avilist_species': len(av),
        'reference_status_counts': mapping['REFERENCE STATUS'].value_counts().to_dict(),
        'matching_rule': 'Exact EBD scientific name/category in declared source API; published Cornell code in latest AviList/target eBird; exact EBD Avibase concept ID equality. No fallback.',
    }
    if source_dir is not None:
        source_dir = Path(source_dir)
        source_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(avilist_file, source_dir / 'avilist.xlsx')
        (source_dir / 'ebird_source.json').write_text(json.dumps(source, sort_keys=True), encoding='utf-8')
        (source_dir / 'ebird_target.json').write_text(json.dumps(target, sort_keys=True), encoding='utf-8')
        (source_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    output_dir = PACKAGE_DIR if output_dir is None else Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # Validate everything first. A failed/interrupted activation cannot silently
    # load an old bundle: the manifest hashes must agree with the current files.
    for name, data in payloads.items():
        temporary = output_dir / f'{name}.tmp'
        temporary.write_bytes(data)
        temporary.replace(output_dir / name)
    temporary = output_dir / 'taxonomy_manifest.json.tmp'
    temporary.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    temporary.replace(output_dir / 'taxonomy_manifest.json')
    return manifest


def load_taxonomy_bundle(directory=None):
    """Read exactly the active, checksummed bundle; never search legacy files."""
    root = Path(directory) if directory is not None else resources.files('eBird2ABAP')
    manifest = json.loads(root.joinpath('taxonomy_manifest.json').read_text(encoding='utf-8'))
    tables = {}
    for name, expected in manifest['files'].items():
        data = root.joinpath(name).read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f'Taxonomy bundle checksum mismatch: {name}; run the explicit update command')
        with root.joinpath(name).open('r', encoding='utf-8') as stream:
            tables[name] = pd.read_csv(stream)
    return tables['ebird_avilist_mapping.csv'], manifest


def check_taxonomy_updates(directory=None):
    _, manifest = load_taxonomy_bundle(directory)
    latest = current_taxonomy_versions()
    return {**latest, 'update_required': any(manifest[key] != value for key, value in latest.items())}


def add_avilist_taxonomy(ebd, return_unmatched=False, *, ebird_version=None,
                         strict=True, report_dir=None, taxonomy_dir=None):
    """Keep EBD Avibase keys, annotate only direct verified matches, report every issue.

    return_unmatched=True is an audit and does not require a version declaration;
    it never exports cards. Normal conversion requires the declared source version.
    strict=False explicitly retains unresolved keys with blank AviList metadata.
    """
    mapping, manifest = load_taxonomy_bundle(taxonomy_dir)
    if (ebird_version is not None or not return_unmatched) and str(ebird_version) != manifest['ebird_source_version']:
        raise ValueError(f"Declare ebird_version={manifest['ebird_source_version']!r} for this bundle; received {ebird_version!r}. Never infer it from observation dates. Rebuild the bundle for a different source version.")
    annotated = ebd.merge(mapping, left_on=['SCIENTIFIC NAME', 'CATEGORY'],
                          right_on=['EBIRD SCIENTIFIC NAME', 'EBIRD CATEGORY'], how='left', validate='many_to_one')
    annotated['AVIBASE ID'] = annotated['TAXON CONCEPT ID']
    annotated['AVILIST MATCH'] = annotated['REFERENCE STATUS'].fillna('source_name_category_not_found')
    linked = annotated['REFERENCE STATUS'].eq('linked')
    annotated.loc[linked, 'AVILIST MATCH'] = 'exact'
    annotated.loc[linked & annotated['TAXON CONCEPT ID'].ne(annotated['EXPECTED AVIBASE ID']), 'AVILIST MATCH'] = 'concept_id_mismatch'
    annotated.loc[annotated['TAXON CONCEPT ID'].isna(), 'AVILIST MATCH'] = 'missing_concept_id'
    fields = ['AVILIST COMMON NAME', 'AVILIST SCIENTIFIC NAME', 'AVILIST ORDER', 'AVILIST FAMILY', 'AVILIST SEQUENCE']
    annotated.loc[annotated['AVILIST MATCH'].ne('exact'), fields] = pd.NA
    annotated['EBIRD TAXONOMY VERSION'] = manifest['ebird_source_version']
    annotated['TARGET EBIRD TAXONOMY VERSION'] = manifest['ebird_target_version']
    annotated['AVILIST VERSION'] = manifest['avilist_version']
    report = annotated.groupby(['SCIENTIFIC NAME', 'CATEGORY', 'TAXON CONCEPT ID',
                               'EBIRD SPECIES CODE', 'EXPECTED AVIBASE ID', 'AVILIST MATCH'], dropna=False).size().reset_index(name='OBSERVATIONS')
    unresolved = report.loc[report['AVILIST MATCH'].ne('exact')].copy()
    summary = {
        'observations': len(annotated), 'unmatched_observations': int(unresolved['OBSERVATIONS'].sum()),
        'source_version_declared': ebird_version, 'ebird_source_version': manifest['ebird_source_version'],
        'ebird_target_version': manifest['ebird_target_version'], 'avilist_version': manifest['avilist_version'],
        'status_counts': annotated['AVILIST MATCH'].value_counts().to_dict(),
    }
    annotated.attrs['taxonomy_summary'] = summary
    if report_dir is not None:
        report_dir = Path(report_dir)
        report_dir.mkdir(parents=True, exist_ok=True)
        report.to_csv(report_dir / 'taxon_matches.csv', index=False)
        unresolved.to_csv(report_dir / 'unresolved_taxa.csv', index=False)
        (report_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
        (report_dir / 'taxonomy_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(f"Taxonomy {manifest['ebird_source_version']} → eBird {manifest['ebird_target_version']} / AviList {manifest['avilist_version']}: {len(annotated) - summary['unmatched_observations']}/{len(annotated)} observations directly matched.")
    if return_unmatched:
        return unresolved
    if summary['unmatched_observations']:
        if strict:
            raise TaxonomyMatchError(unresolved, summary)
        warnings.warn(f"Retaining {summary['unmatched_observations']} unresolved observations by source Avibase key with blank AviList metadata; no fallback.", UserWarning, stacklevel=2)
    return annotated
