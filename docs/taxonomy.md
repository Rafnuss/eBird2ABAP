# Taxonomy pipeline

## Policy and active releases

There is no approved Avibase-to-ADU mapping yet. The runtime never reads `matched_species.csv`, assigns an ADU code, or substitutes an older taxonomy. `Spp` remains the original EBD `TAXON CONCEPT ID` (an Avibase concept ID).

The single active bundle currently declares:

- EBD source taxonomy: **eBird 2025**, explicitly confirmed by the user.
- Target eBird/Clements taxonomy: **2026**, identified as latest by the eBird API during the update.
- Target taxonomy and names: **AviList v2026**, from the supplied extended workbook published on 20 October 2026.

AviList 2026's `How to use` sheet defines its Cornell species-code field as a published link for matching species concepts. It also notes a specific differing-ID exception. We do not infer concept equivalence from the code alone: the EBD Avibase ID must equal the linked AviList Avibase ID. This prevents a published code, spelling similarity, or familiar scientific name from concealing an ID disagreement.

References: [AviList v2026](https://www.avilist.org/checklist/v2026/), [official eBird API documentation](https://documenter.getpostman.com/view/664302/S1ENwy59), and [eBird's explanation of concept identifiers](https://support.ebird.org/en/support/solutions/articles/48000804865). The eBird taxonomy API provides species codes, names, and categories, but no Avibase concept IDs in the responses inspected. Its 2025 endpoint is deliberately used to validate the declared source EBD; this is not fallback to a legacy local file.

## Direct-match conditions

For an observation to receive AviList names and taxonomy, all of these must hold:

1. Its exact scientific name and category identify one row in the declared source eBird API reference.
2. The source species code has one explicit species link in the supplied AviList workbook.
3. That code exists at species rank in the current target eBird API reference.
4. Its EBD `TAXON CONCEPT ID` is identical to the linked AviList species `AVIBASE ID`.

Scientific names can change between releases when the concept ID agrees; target names come only from AviList. There is no fuzzy matching, name-only AviList join, synonym guessing, parent-species roll-up, split/lump inference, geographic reassignment, or old-file fallback. Subspecies, ISSFs, domestics, hybrids, slashes, and spuhs are not automatically converted to species. The complete source API reference is retained in the crosswalk, including unresolved categories.

## Update explicitly

From the repository root:

```bash
uv run python scripts/build_ebird_avilist_mapping.py \
  --avilist /path/to/AviList-v2026-20Oct2026-extended-version.xlsx \
  --avilist-version 2026 \
  --ebird-version 2025
```

The workbook and its exact version are required; no directory search selects an older file. The named sheet must exist and declare a Clements crosswalk to the latest eBird API release. Changing the source EBD version requires rebuilding the bundle with that explicit source version.

The updater fetches source and current target API references, rejects ambiguous source keys, duplicate AviList concept IDs, and ambiguous published code links, then activates these files together:

- `eBird2ABAP/ebird_avilist_mapping.csv`: complete source-API crosswalk and reference statuses.
- `eBird2ABAP/avilist_reference.csv`: current AviList species reference.
- `eBird2ABAP/taxonomy_manifest.json`: source/target versions, source URL, workbook checksum, API checksums, output checksums, update time, and status counts.

Raw snapshots of the selected workbook and both API references are saved under ignored `data/reference/taxonomy/current/`, with their manifest. Those snapshots are for provenance; conversion never searches them for a fallback. The packaged CSV/JSON files are sufficient for deterministic offline conversion. File hashes are verified whenever the bundle loads. Network or validation failures before activation preserve the previous bundle; an interrupted file replacement is detected by a manifest checksum mismatch rather than silently loading a mixture.

## Check freshness separately

```bash
uv run python scripts/build_ebird_avilist_mapping.py --check
```

This checks current published releases without changing the selected sources. An API or website failure returns a nonzero exit status and `freshness: unverified`; it does not mean the bundle is up to date. During this task, the AviList website returned HTTP 403 to Python requests, although the current 2026 release was independently verified through the web source. The workflow therefore requires explicit workbook/version selection and does not claim unattended AviList freshness verification when that website is unavailable. A successful build validates the declared crosswalk against the latest eBird API; it does not certify that no newer minor AviList file exists.

No conversion makes an implicit network update. To adopt a new release, obtain its current official workbook, run the update command, review the statuses/diff, and rerun your EBD audit. This makes source changes inspectable rather than silently altering research results.

## Audit before conversion

```python
from eBird2ABAP import read_EBD, add_avilist_taxonomy

ebd = read_EBD("data/ebd/your-release/", nrows=10000)
issues = add_avilist_taxonomy(
    ebd,
    ebird_version="2025",
    return_unmatched=True,
    report_dir="export/taxonomy_review",
)
```

The report directory contains `taxon_matches.csv`, `unresolved_taxa.csv`, `summary.json`, and the exact `taxonomy_manifest.json`. Every reported taxon includes the original scientific name, category, original concept ID, candidate eBird code, expected AviList ID, observation count, and reason. `return_unmatched=True` performs an audit only; without a declared source version its summary explicitly records that no EBD version was declared. It is not evidence that the EBD was produced with that taxonomy.

| Status | Meaning/action |
| --- | --- |
| `exact` | All direct-match conditions pass |
| `source_name_category_not_found` | The exact EBD name/category pair is not in the source API reference; check source version and EBD naming conventions. This does not prove the concept is absent from eBird. In particular, EBD can show a parent scientific name for an ISSF. |
| `source_ebird_not_species` | Source category is not species; no parent roll-up is attempted |
| `no_published_avilist_link` | No explicit Cornell-code link is provided in current AviList |
| `code_absent_from_target_ebird` | Source code is no longer present in the current target eBird reference |
| `target_ebird_not_species` | Source code now represents a non-species category in the target reference |
| `concept_id_mismatch` | EBD and candidate AviList concept IDs differ; matching names are insufficient |
| `missing_concept_id` | There is no original Avibase key to preserve; export cannot safely proceed |

## Strict and explicitly permissive conversion

```python
from eBird2ABAP import ebird2abap

cards = ebird2abap(
    "data/ebd/your-release/",
    JSON_file="export/cards.json",
    ebird_version="2025",
)
```

Strict mode is the default. Any unresolved observation raises `TaxonomyMatchError` after writing the report to `export/cards_taxonomy/`. Its `report` and `summary` attributes are available interactively. No new card JSON is written after a strict taxonomy failure; an older output file at the same path is not proof the new run succeeded.

After reviewing the issues, `strict_taxonomy=False` explicitly allows observations to retain their original Avibase keys with blank AviList names and classification where the direct match is unresolved. It issues a warning and keeps the reports. There is no alternative lookup in this mode. A missing source concept ID still prevents record export. JSON records include `TaxonomyStatus`, `AviListVersion`, `eBirdSourceTaxonomyVersion`, and `eBirdTargetTaxonomyVersion` so a blank name cannot be mistaken for a verified match.

`TotalSpp` in permissive exports counts retained distinct source taxon keys, which may include non-species concepts; it is not automatically a verified species-richness estimate. Taxonomy reports cover all input observations, including checklists later excluded by effort/card rules. A row-limited input may truncate checklists and is only a compatibility smoke test.

## Initial compatibility feedback

The active crosswalk contains 17,891 source eBird taxa and 11,172 AviList species. Of the source taxa, 11,081 have published, species-level candidate links; a candidate still needs the EBD concept-ID check at runtime.

Two 10,000-observation samples from the existing files were audited against the declared 2025 source and 2026 target:

| Input | Direct observations | Unresolved observations |
| --- | ---: | ---: |
| June 2026 regional EBD | 9,399 | 601 |
| October 28 Project 1056 export | 8,859 | 1,141 |

The regional sample includes 17 concept-ID mismatches; other issues include missing code links, retired or non-species target codes, and source name/category discrepancies. The Project 1056 sample includes many ISSF records whose EBD parent scientific name does not identify the API's more specific source taxon. These are explicit limitations, not a reason to silently infer the parent species. Full diagnosis of those records requires an authoritative source-taxonomy reference containing their Avibase IDs or a documented EBD taxon identifier that directly identifies their API code.

The reports are local generated outputs under `export/taxonomy_review/`. No private EBD rows or observation locations are included in the packaged taxonomy reference or committed documentation.
