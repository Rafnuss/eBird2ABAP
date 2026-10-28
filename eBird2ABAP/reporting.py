"""Repeatable local EBD quality reports; no notebook or public data upload."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
from html import escape
import json
import platform
from pathlib import Path
import warnings

import pandas as pd

from .checklists import MEMBER_COLUMNS, collapse_shared_checklists, effort_by_day
from .ebird2card import _resolve_EBD_file, chk2valid_card, ebd2chk, iter_EBD
from .taxonomy import add_avilist_taxonomy, load_taxonomy_bundle


def generate_report(file, output_dir, *, ebird_version, nrows=None, chunksize=100000, source_kind="ebd"):
    """Read observations in chunks; retain checklist metadata and taxon totals.

    Full releases still require memory proportional to their checklist metadata,
    but observation rows are not accumulated. Prefix reports are labelled as such.
    Outputs are local and must not be uploaded to other locations implicitly.
    """
    from importlib.metadata import version
    from matplotlib.figure import Figure

    file = _resolve_EBD_file(file)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    _, manifest = load_taxonomy_bundle()
    if str(ebird_version) != manifest['ebird_source_version']:
        raise ValueError('Report EBD source version must match the active taxonomy bundle')
    counts = Counter()
    member_rows = []
    seen_members = set()
    observations = 0
    for chunk in iter_EBD(file, nrows=nrows, chunksize=chunksize):
        observations += len(chunk)
        for row in chunk[MEMBER_COLUMNS].drop_duplicates().itertuples(index=False, name=None):
            key = tuple(None if pd.isna(value) else value for value in row)
            if key not in seen_members:
                seen_members.add(key)
                member_rows.append(key)
        grouped = chunk.groupby(['SCIENTIFIC NAME', 'CATEGORY', 'TAXON CONCEPT ID'], dropna=False).size()
        counts.update({tuple(None if pd.isna(value) else value for value in key): int(count) for key, count in grouped.items()})
        print(f'Report: {observations:,} observation rows read', flush=True)
    members = pd.DataFrame(member_rows, columns=MEMBER_COLUMNS)
    members['OBSERVATION DATE'] = pd.to_datetime(members['OBSERVATION DATE'])
    members['OBSERVATION DATETIME'] = pd.to_datetime(members['OBSERVATION DATETIME'])
    events, members = collapse_shared_checklists(members.assign(**{'TAXON CONCEPT ID': 'metadata_only'}))
    chk = ebd2chk(events)
    cards = chk2valid_card(chk)
    elapsed_minutes = effort_by_day(chk, ["PENTAD", "OBSERVER ID"])["DURATION MINUTES"].sum()
    reported_minutes = chk.loc[chk["QUALIFIES EFFORT"], "DURATION MINUTES"].sum()
    taxa = pd.DataFrame([(*key, value) for key, value in counts.items()],
                        columns=['SCIENTIFIC NAME', 'CATEGORY', 'TAXON CONCEPT ID', 'RAW OBSERVATIONS'])
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="Retaining .* unresolved observations", category=UserWarning)
        annotated = add_avilist_taxonomy(taxa, ebird_version=ebird_version, strict=False)
    statuses = annotated.groupby('AVILIST MATCH')['RAW OBSERVATIONS'].sum().sort_values(ascending=False)
    protocols = chk['PROTOCOL TYPE'].value_counts()
    with file.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    summary = {
        'package_version': version('eBird2ABAP'), 'python_version': platform.python_version(),
        'dependency_versions': {name: version(name) for name in ['numpy', 'pandas', 'geopandas', 'shapely', 'pyproj', 'requests', 'matplotlib']}, 'generated_at_utc': datetime.now(timezone.utc).isoformat(),
        'input_file': file.name, 'input_sha256': digest, 'input_bytes': file.stat().st_size,
        'scope': 'prefix' if nrows is not None else 'full_file', 'source_kind': source_kind, 'requested_nrows': nrows,
        'rows_read': observations, 'raw_checklists': int(members['SAMPLING EVENT IDENTIFIER'].nunique()),
        'independent_events': len(chk), 'shared_events': int(chk['GROUP IDENTIFIER'].notna().sum()),
        'metadata_conflicts': int(chk['SHARED METADATA CONFLICT'].sum()),
        'cross_pentad_time_conflicts': int(chk['CROSS PENTAD TIME CONFLICT'].sum()),
        'missing_start_times': int(chk['OBSERVATION DATETIME'].isna().sum()),
        'missing_distances': int(chk['EFFORT DISTANCE KM'].isna().sum()),
        'qualifying_events': int(chk['QUALIFIES EFFORT'].sum()), 'candidate_cards': len(cards),
        'qualifying_elapsed_hours': round(float(elapsed_minutes) / 60, 2),
        'overlap_minutes_removed': round(float(reported_minutes - elapsed_minutes), 2),
        'spatial_status_counts': chk['SPATIAL STATUS'].value_counts().to_dict(),
        'taxonomy_observation_counts': {key: int(value) for key, value in statuses.items()},
        'source_ebird_version': str(ebird_version), 'target_ebird_version': manifest['ebird_target_version'],
        'avilist_version': manifest['avilist_version'],
        'taxonomy_manifest_sha256': hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(),
        'limitations': [
            'Candidate cards are effort-based and are not verified ABAP submissions.',
            'Spatial screening is conditional on reported locality and movement; no GPS track was supplied.',
            'All observer IDs are retained as provenance, not proof of equal participation.',
            'Taxonomy counts use raw observation rows; shared observations can repeat in these counts.',
            'A prefix can truncate checklists and shared groups; prefix card counts are not release estimates.',
        ],
    }
    (output_dir / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    (output_dir / 'taxonomy_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    annotated.to_csv(output_dir / 'taxon_matches.csv', index=False)
    annotated.loc[annotated['AVILIST MATCH'].ne('exact')].to_csv(output_dir / 'unresolved_taxa.csv', index=False)
    chk.to_csv(output_dir / 'checklist_quality.csv', index=False)
    members.to_csv(output_dir / 'checklist_members.csv', index=False)
    cards.to_csv(output_dir / 'candidate_cards.csv', index=False)
    for name, values, label in [('protocols', protocols, 'Independent events'), ('taxonomy', statuses, 'Raw observation rows')]:
        fig = Figure(figsize=(9, max(3, len(values) * 0.45)))
        axis = fig.subplots()
        if not values.empty:
            axis.barh(values.index.astype(str), values.values, color='#276b8f')
            axis.invert_yaxis()
        axis.set_xlabel(label)
        axis.spines[['top', 'right']].set_visible(False)
        fig.tight_layout()
        fig.savefig(output_dir / f'{name}.svg')
    metric_keys = ['rows_read', 'raw_checklists', 'independent_events', 'shared_events', 'metadata_conflicts',
                   'missing_start_times', 'missing_distances', 'qualifying_events', 'qualifying_elapsed_hours', 'overlap_minutes_removed', 'candidate_cards']
    labels = ['Observation rows', 'Source checklists', 'Independent events', 'Shared events', 'Metadata conflicts',
              'Unknown start times', 'Unknown distances', 'Qualifying events', 'Elapsed qualifying hours',
              'Overlapping minutes removed', 'Candidate cards']
    values = [f'{summary[key]:,.2f}' if isinstance(summary[key], float) else f'{summary[key]:,}' for key in metric_keys]
    metrics = pd.DataFrame({'Metric': labels, 'Value': values})
    status_table = statuses.rename_axis('Status').reset_index(name='Raw observation rows')
    scope = ('SYNTHETIC EXAMPLE — not real EBD observations' if source_kind == 'synthetic' else
             'PREFIX SAMPLE — not a complete release' if nrows is not None else 'Complete supplied file')
    html = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>EBD quality report</title><style>body{{font:17px/1.6 system-ui,sans-serif;max-width:1050px;margin:3rem auto;padding:0 1.5rem;color:#193243;background:#fafcfd}}h1,h2{{line-height:1.2}}table{{border-collapse:collapse;width:100%;margin:1rem 0 2rem}}th,td{{padding:.5rem .8rem;text-align:left;border-bottom:1px solid #ccd8df}}th{{background:#e8f0f5}}img{{max-width:100%}}.scope{{border-left:5px solid #b87815;padding:1rem;background:#fff5e2}}code{{overflow-wrap:anywhere}}footer{{margin-top:3rem;font-size:.9rem}}</style></head><body>
<h1>EBD quality report</h1><p class="scope"><strong>{escape(scope)}</strong><br>{escape(file.name)}</p>
<p>eBird source {escape(str(ebird_version))} → eBird target {escape(manifest['ebird_target_version'])} / AviList {escape(manifest['avilist_version'])}. Package {escape(summary['package_version'])}.</p>
<h2>Sampling and effort</h2>{metrics.to_html(index=False, border=0)}<img src="protocols.svg" alt="Independent events by protocol">
<h2>Taxonomy compatibility</h2>{status_table.to_html(index=False, border=0)}<img src="taxonomy.svg" alt="Raw observations by taxonomy matching status">
<h2>Interpretation</h2><ul>{''.join('<li>' + escape(text) + '</li>' for text in summary['limitations'])}</ul>
<h2>Inspect the results</h2><p><a href="summary.json">Machine-readable summary</a> · <a href="unresolved_taxa.csv">Unresolved taxa</a> · <a href="checklist_quality.csv">Event quality</a> · <a href="checklist_members.csv">Group membership</a> · <a href="candidate_cards.csv">Candidate cards</a> · <a href="taxonomy_manifest.json">Reference manifest</a></p>
<footer>Generated {escape(summary['generated_at_utc'])}. Source SHA256: <code>{digest}</code>. Generated data remain local.</footer></body></html>'''
    (output_dir / 'index.html').write_text(html, encoding='utf-8')
    return summary
