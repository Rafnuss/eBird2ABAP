"""Explicit update of the one active eBird/AviList taxonomy bundle."""

import argparse
import json
from pathlib import Path
import requests

from eBird2ABAP.taxonomy import check_taxonomy_updates, update_taxonomy

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--avilist', help='Path to the current official extended AviList workbook')
parser.add_argument('--avilist-version', help='Explicit release of the current official workbook, e.g. 2026')
parser.add_argument('--ebird-version', help='Declared taxonomy version of the input EBD (not its observation year)')
parser.add_argument('--check', action='store_true', help='Check current published versions without changing files')
args = parser.parse_args()
if args.check:
    try:
        result = check_taxonomy_updates()
    except (requests.RequestException, ValueError) as error:
        print(json.dumps({'freshness': 'unverified', 'error': str(error)}, indent=2))
        raise SystemExit(2)
else:
    if not args.avilist or not args.ebird_version or not args.avilist_version:
        parser.error('--avilist, --avilist-version and --ebird-version are required to update; no file search or fallback')
    result = update_taxonomy(args.avilist, ebird_version=args.ebird_version, avilist_version=args.avilist_version,
        source_dir=Path(__file__).resolve().parents[1] / 'data/reference/taxonomy/current')
print(json.dumps(result, indent=2))
