"""Generate a local EBD diagnostic report from an explicitly selected release.

Run: uv run python scripts/report_ebd.py --input data/ebd/release/ --output export/report --ebird-version 2025
"""

import argparse
from pathlib import Path

from eBird2ABAP import generate_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--ebird-version', required=True)
parser.add_argument('--nrows', type=int, help='Optional prefix sample, labelled in the report')
args = parser.parse_args()
summary = generate_report(args.input, args.output, ebird_version=args.ebird_version, nrows=args.nrows)
print(f"Report: {args.output / 'index.html'}")
print(f"{summary['independent_events']} independent events; {summary['candidate_cards']} candidate cards")
