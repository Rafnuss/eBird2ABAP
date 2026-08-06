# Data guide

## EBD sources

Raw EBD files are not stored in Git. Keep all eBird downloads under `data/ebd/`:

```text
data/ebd/
├── ebd_AFR_relJun-2026/               # general African EBD release
└── project_1056_african_bird_atlas/   # African Bird Atlas Project export
```

The EBD downloader saves general releases directly in `data/ebd/`.

## Download a general African EBD release

From the repository root:

```bash
uv run python -c "from eBird2ABAP import download_EBD; print(download_EBD())"
```

For a specific older release:

```bash
uv run python -c "from eBird2ABAP import download_EBD; print(download_EBD(year='2024', month='Dec'))"
```

The function downloads a `.tar` archive, extracts it automatically, and keeps both the archive and extracted release directory. Without an explicit release, it tries the previous month then up to three older months.

The species observations file is normally inside a release directory, for example:

```text
data/ebd/ebd_AFR_relJun-2026/ebd_AFR_relJun-2026.txt.gz
```

## Download manually from eBird

Manual eBird downloads are ZIP files. Unzip them before use and place the extracted release directory under `data/ebd/`.

For the [African Bird Atlas Project](https://ebird.org/projects/1056), keep the full export together under:

```text
data/ebd/project_1056_african_bird_atlas/
```

Use `project-1056-report-*.txt` for conversion. The accompanying `project-1056-sampling-report-*.txt` is checklist-level metadata and is not a conversion input.

`read_EBD()` and `ebird2abap()` accept an extracted release directory, a `.txt`, or a `.txt.gz` file. With a directory, they select the species-level file and ignore sampling reports.

## Other project data

`data/` also holds ABAP reference data, geographic inputs, pentad grids, and species-matching material. These are separate from EBD downloads. Legacy material belongs in `archive/`.

Raw EBD data, local exports, and restricted data are ignored by Git. Review eBird terms of use before sharing data or derived products.
