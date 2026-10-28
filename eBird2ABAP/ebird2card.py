import pandas as pd
import numpy as np

import os
import datetime
import gzip
from pathlib import Path

import requests
import tarfile

from .pentad import latlng2pentad, pentad2latlng
from .checklists import EVENT_METADATA, collapse_shared_checklists, effort_by_day, qualifies_effort, cross_pentad_overlaps
from pyproj import Geod
from .taxonomy import add_avilist_taxonomy, load_taxonomy_bundle

DEFAULT_EBD_DIR = Path("data") / "ebd"


def _is_species_ebd_file(path):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "rt", encoding="utf-8", errors="ignore") as f:
        columns = {column.strip().strip('"') for column in f.readline().split("\t")}
    return {"SAMPLING EVENT IDENTIFIER", "SCIENTIFIC NAME"}.issubset(columns)


def _resolve_EBD_file(file):
    path = Path(file)
    if path.is_file():
        return path
    if path.is_dir():
        candidates = sorted(
            candidate
            for candidate in path.iterdir()
            if candidate.is_file()
            and candidate.name.endswith((".txt", ".txt.gz"))
            and "sampling" not in candidate.name.lower()
            and _is_species_ebd_file(candidate)
        )
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise FileNotFoundError(
                f"No species-level EBD .txt or .txt.gz file found in {path}"
            )
        raise ValueError(
            f"More than one species-level EBD file found in {path}: {candidates}"
        )
    raise FileNotFoundError(f"EBD file or directory does not exist: {path}")


def ebird2abap(EBD_file, JSON_file=None, exportCSV=False, *,
               observer_email=None, observer_no=None,
               ebird_version=None, strict_taxonomy=True):
    """Convert species-level EBD data, write exports, and return the card table.

    JSON_file controls the output directory and basename of optional CSV files.
    Receiving-account details remain unknown unless supplied explicitly.
    """
    EBD_file = _resolve_EBD_file(EBD_file)
    basename = os.path.basename(EBD_file).removesuffix(".txt.gz").removesuffix(".txt")
    print("Reading EBD file...")
    ebd, members = read_EBD(EBD_file, return_members=True)

    print("Adding AviList taxonomy...")
    if JSON_file is None:
        JSON_file = f"{basename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    JSON_file = Path(JSON_file)
    ebd = add_avilist_taxonomy(
        ebd, ebird_version=ebird_version, strict=strict_taxonomy,
        report_dir=JSON_file.with_name(f"{JSON_file.stem}_taxonomy"),
    )

    report_dir = JSON_file.with_name(f"{JSON_file.stem}_taxonomy")
    members.to_csv(report_dir / "checklist_members.csv", index=False)
    print("Computing checklists...")
    chk = ebd2chk(ebd)
    chk.to_csv(report_dir / "checklist_quality.csv", index=False)

    print("Checking validity of cards...")
    card_valid = chk2valid_card(chk)

    print("Converting valid cards to CHK cards...")
    chk_card = valid_card2chk_card(chk, card_valid)

    print("Converting CHK cards to card check...")
    card_chk = chk_card2card_chk(chk_card, card_valid)

    print("Converting CHK cards to EBD formatted units...")
    ebd_f_u = chk_card2ebd_f_u(ebd, chk_card)

    print("Converting EBD formatted units to card expressions...")
    card_exp = ebd_f_u2card_exp(
        card_chk, ebd_f_u, observer_email=observer_email, observer_no=observer_no
    )

    print("Converting card expressions to JSON format...")
    json_data = card_exp.to_json(orient="records", indent=2)

    JSON_file = Path(JSON_file)
    JSON_file.parent.mkdir(parents=True, exist_ok=True)
    print(f"Writing JSON data to {JSON_file}...")
    JSON_file.write_text(json_data, encoding="utf-8")

    if exportCSV:
        card_chk.to_csv(JSON_file.with_name(f"{JSON_file.stem}_cards.csv"), index=False)
        ebd_f_u[["CARD", "AVIBASE ID", "SEQ"]].to_csv(
            JSON_file.with_name(f"{JSON_file.stem}_records.csv"), index=False
        )

    print("Process completed successfully.")
    return card_exp


def download_EBD(year=None, month=None, output_dir=DEFAULT_EBD_DIR):
    if (year is None) != (month is None):
        raise ValueError("year and month must be provided together")

    if year is None and month is None:
        today = datetime.date.today()
        release_month = today.replace(day=1) - datetime.timedelta(days=1)
        candidates = []
        for _ in range(4):
            candidates.append((release_month.strftime("%Y"), release_month.strftime("%b")))
            release_month = release_month.replace(day=1) - datetime.timedelta(days=1)
    else:
        candidates = [(year, month)]

    os.makedirs(output_dir, exist_ok=True)

    for i, (year, month) in enumerate(candidates):
        url = f"https://download.ebird.org/ebd/prepackaged/ebd_AFR_rel{month}-{year}.tar"
        filename = os.path.basename(url)
        filepath = os.path.join(output_dir, filename)
        print(f"Checking African EBD release {month}-{year}...", flush=True)

        with requests.get(url, stream=True, timeout=(30, 120)) as response:
            if response.status_code == 404 and i < len(candidates) - 1:
                print("Not available; trying an older release.", flush=True)
                continue
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0)) or None
            downloaded_size = 0
            next_progress = 0
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size:
                            progress = int(downloaded_size / total_size * 100)
                            if progress >= next_progress:
                                print(f"\rDownloading {filename}: {progress:3d}%", end="", flush=True)
                                next_progress += 5
                        elif downloaded_size // (100 * 1024 * 1024) > next_progress:
                            next_progress = downloaded_size // (100 * 1024 * 1024)
                            print(f"\rDownloading {filename}: {next_progress * 100} MB", end="", flush=True)
            print()
        break
    else:
        raise FileNotFoundError("No African EBD release found in the last four release months")

    extract_dir = os.path.join(output_dir, f"ebd_AFR_rel{month}-{year}")
    os.makedirs(extract_dir, exist_ok=True)
    with tarfile.open(filepath, "r") as tar:
        tar.extractall(extract_dir, filter="data")

    return filepath


def iter_EBD(file, *, nrows=None, chunksize=100000):
    """Yield raw normalized EBD chunks; shared groups are not collapsed per chunk."""
    file = _resolve_EBD_file(file)
    columns = pd.read_csv(file, sep="\t", nrows=0).columns
    protocol_column = "PROTOCOL TYPE" if "PROTOCOL TYPE" in columns else "PROTOCOL NAME"
    usecols = ["SAMPLING EVENT IDENTIFIER", "GROUP IDENTIFIER", "SCIENTIFIC NAME", "TAXON CONCEPT ID", "CATEGORY",
               "LATITUDE", "LONGITUDE", "OBSERVATION DATE", "TIME OBSERVATIONS STARTED", protocol_column,
               "DURATION MINUTES", "EFFORT DISTANCE KM", "ALL SPECIES REPORTED", "OBSERVER ID"]
    for ebd in pd.read_csv(file, sep="\t", usecols=usecols, nrows=nrows, chunksize=chunksize):
        ebd = ebd.rename(columns={protocol_column: "PROTOCOL TYPE"})
        ebd["OBSERVATION DATE"] = pd.to_datetime(ebd["OBSERVATION DATE"]).dt.normalize()
        ebd["DURATION MINUTES"] = ebd["DURATION MINUTES"].astype(float)
        ebd["OBSERVATION DATETIME"] = pd.to_datetime(
            ebd["OBSERVATION DATE"].dt.strftime("%Y-%m-%d") + " " + ebd["TIME OBSERVATIONS STARTED"],
            format="%Y-%m-%d %H:%M:%S",
        )
        ebd["EVENT ID"] = ebd["GROUP IDENTIFIER"].astype("string").fillna(ebd["SAMPLING EVENT IDENTIFIER"].astype("string"))
        yield ebd


def read_EBD(file, nrows=None, *, return_members=False):
    """Read EBD, collapse independent events by Avibase concept, retain member IDs.

    ``return_members=True`` also returns the original checklist metadata table.
    Missing start times remain unknown and cannot establish timed effort.
    """
    raw = pd.concat(iter_EBD(file, nrows=nrows), ignore_index=True)
    ebd, members = collapse_shared_checklists(raw)
    return (ebd, members) if return_members else ebd


def load_avilist_mapping():
    """Return the single checksummed active crosswalk."""
    return load_taxonomy_bundle()[0]


def ebd2chk(ebd):
    """One independent event, with an explicit conservative spatial screen.

    Stationary uses the protocol's 30 m movement allowance. Other protocols
    require a known distance. Distance is a screening radius, not track proof
    or GPS accuracy; the selected eBird location may not be the route start.
    """
    columns = ["SAMPLING EVENT IDENTIFIER", "OBSERVER ID", *EVENT_METADATA,
               "EVENT ID", "GROUP IDENTIFIER", "SOURCE CHECKLIST IDS", "SOURCE OBSERVER IDS", "SHARED METADATA CONFLICT"]
    chk = ebd[columns].drop_duplicates("SAMPLING EVENT IDENTIFIER").sort_values("OBSERVATION DATETIME", kind="stable").reset_index(drop=True)
    chk["KEEP PROTOCOL"] = chk["PROTOCOL TYPE"].isin(["Stationary", "Traveling"])
    chk["PENTAD"] = pd.Series(latlng2pentad(chk["LATITUDE"], chk["LONGITUDE"]), dtype=str)
    lat, lng = pentad2latlng(chk["PENTAD"])
    north, south = np.array(lat) + 1/24, np.array(lat) - 1/24
    west, east = np.array(lng) - 1/24, np.array(lng) + 1/24
    geod = Geod(ellps="WGS84")
    edge_distances = [
        geod.inv(chk["LONGITUDE"].to_numpy(), chk["LATITUDE"].to_numpy(), chk["LONGITUDE"].to_numpy(), edge)[2]
        for edge in [north, south]
    ] + [
        geod.inv(chk["LONGITUDE"].to_numpy(), chk["LATITUDE"].to_numpy(), edge, chk["LATITUDE"].to_numpy())[2]
        for edge in [west, east]
    ]
    chk["EDGE DISTANCE M"] = np.min(edge_distances, axis=0)
    radius = chk["EFFORT DISTANCE KM"] * 1000
    radius = radius.where(chk["PROTOCOL TYPE"].ne("Stationary"), np.maximum(radius.fillna(0), 30.0))
    chk["SPATIAL STATUS"] = np.where(radius.isna(), "unknown_distance",
                                     np.where(radius.le(chk["EDGE DISTANCE M"]), "screen_pass", "possible_boundary_crossing"))
    chk["KEEP PENTAD"] = chk["SPATIAL STATUS"].eq("screen_pass") & ~chk["SHARED METADATA CONFLICT"]
    chk["QUALIFIES EFFORT"] = qualifies_effort(chk)
    chk["CROSS PENTAD TIME CONFLICT"] = cross_pentad_overlaps(chk)
    return chk


def chk2valid_card(chk):
    # Non-overlapping elapsed effort, split across calendar dates.
    checkday = effort_by_day(chk, ["PENTAD", "OBSERVER ID"])
    if checkday.empty:
        return checkday[["PENTAD", "OBSERVER ID", "OBSERVATION DATE"]].assign(CARD=pd.Series(dtype=str))

    starts = chk.loc[qualifies_effort(chk), ["PENTAD", "OBSERVER ID", "OBSERVATION DATE"]].drop_duplicates()
    starts["CAN START CARD"] = True
    checkday = checkday.merge(starts, how="left", on=["PENTAD", "OBSERVER ID", "OBSERVATION DATE"])
    checkday["CAN START CARD"] = checkday["CAN START CARD"].eq(True)

    # Sort the checklist by date
    checkday = checkday.sort_values(by=["OBSERVATION DATE"], kind="stable")

    # Create additional columns
    checkday["pentad_observer"] = checkday["PENTAD"] + "_" + checkday["OBSERVER ID"]
    checkday["pentad_observer_date"] = (
        checkday["PENTAD"]
        + "_"
        + checkday["OBSERVER ID"]
        + "_"
        + checkday["OBSERVATION DATE"].dt.strftime("%Y%m%d")
    )

    # Do a first filter to eliminate all pentad_observer witout sufficient total duration time. (Aim is to just reduce the computation later)
    pentad_observer_duration = checkday.groupby(["pentad_observer"])[
        "DURATION MINUTES"
    ].sum()
    pentad_observer_duration_index = pentad_observer_duration[
        pentad_observer_duration >= 2 * 60
    ].index
    checkday_long = checkday[
        checkday["pentad_observer"].isin(pentad_observer_duration_index)
    ]

    if checkday_long.empty:
        return checkday_long[["PENTAD", "OBSERVER ID", "OBSERVATION DATE"]].assign(CARD=pd.Series(dtype=str))

    # Apply the date-window rule separately for each pentad and observer.
    checkday_long_card = (
        checkday_long.groupby("pentad_observer")
        .apply(checkday_pentad_observer, include_groups=False)
        .reset_index()
    )

    # Create the DataFrame of all valid card
    card_valid = checkday_long_card[
        checkday_long_card["CARD"] == checkday_long_card["pentad_observer_date"]
    ][["PENTAD", "OBSERVER ID", "OBSERVATION DATE", "CARD"]]

    # Sort by card
    card_valid = card_valid.sort_values(by="CARD", kind="stable")

    return card_valid


# To find all pentad with sufficient duration effort (i.e, a sum of 2h over 5 days period), we apply this function for each pentad_observer.
def checkday_pentad_observer(df):
    """Select chronological, non-overlapping cards with 120 minutes in five days.

    Failed windows advance one date; successful windows consume all their dates.
    Searchsorted and cumulative effort avoid an n-by-n date-distance matrix.
    """
    df = df.sort_values("OBSERVATION DATE").copy()
    df["CARD"] = ""
    dates = df["OBSERVATION DATE"].to_numpy()
    ends = np.searchsorted(dates, dates + np.timedelta64(5, "D"))
    effort = np.concatenate(([0], df["DURATION MINUTES"].to_numpy().cumsum()))
    start = 0
    while start < len(df):
        end = ends[start]
        if "CAN START CARD" in df and not df.iloc[start]["CAN START CARD"]:
            start += 1
            continue
        if effort[end] - effort[start] >= 120:
            df.iloc[start:end, df.columns.get_loc("CARD")] = df.iloc[start]["pentad_observer_date"]
            start = end
        else:
            start += 1
    return df


def valid_card2chk_card(chk, card_valid):
    # Create Card dataframe by aggregating all checklists
    # We take back `chk` where all checklists (i.e., including the incidentals, stationary, etc...) and find if they contribute to an existing full card.
    # Filter for checklist to keep: within pentad and and pentad and observer present in the valid card list
    chk_keep = chk[
        (chk["KEEP PENTAD"])
        & (
            (chk["PENTAD"] + chk["OBSERVER ID"]).isin(
                (card_valid["PENTAD"] + card_valid["OBSERVER ID"])
            )
        )
    ]

    # Combine all possible checklits with the valid card based on observer and pentad.
    # This will create duplicate checklist with all cards submitted by the same observer, same pentad, but any date
    chk_card = pd.merge(
        chk_keep,  # .loc[:,['OBSERVER ID', 'PENTAD', "SAMPLING EVENT IDENTIFIER", "OBSERVATION DATE"]],
        card_valid,
        on=["OBSERVER ID", "PENTAD"],
        suffixes=("_chk", "_card"),
        how="left",
    )

    # Filter the checklist for checklist beeing within the 5 days of the card so that there will be a single checklist-card now
    duration = (
        chk_card["OBSERVATION DATE_chk"] - chk_card["OBSERVATION DATE_card"]
    ).dt.days
    chk_card = chk_card[(duration >= 0) & (duration < 5)].copy()
    stop = chk_card["OBSERVATION DATE_card"] + pd.Timedelta(days=5)
    reported_end = chk_card["OBSERVATION DATETIME"] + pd.to_timedelta(chk_card["DURATION MINUTES"], unit="m")
    clipped = reported_end.gt(stop)
    chk_card.loc[clipped, "DURATION MINUTES"] = (stop[clipped] - chk_card.loc[clipped, "OBSERVATION DATETIME"]).dt.total_seconds() / 60
    chk_card.loc[clipped & chk_card["EFFORT DISTANCE KM"].ne(0), "EFFORT DISTANCE KM"] = np.nan
    return chk_card


def _unique_members(values):
    """Flatten event memberships without assigning individual participation effort."""
    return sorted({member for group in values for member in group})


def chk_card2card_chk(chk_card, card_valid):
    """Aggregate card metadata; only qualifying interval union counts as effort."""
    card_chk = chk_card.groupby("CARD").agg(**{
        "SAMPLING EVENT IDENTIFIER_list": ("SAMPLING EVENT IDENTIFIER", list),
        "SOURCE CHECKLIST IDS": ("SOURCE CHECKLIST IDS", _unique_members),
        "SOURCE OBSERVER IDS": ("SOURCE OBSERVER IDS", _unique_members),
        "EVENT IDS": ("EVENT ID", list),
        "OBSERVATION DATETIME_min": ("OBSERVATION DATETIME", "min"),
    }).reset_index()
    daily = effort_by_day(chk_card, ["CARD"])
    daily = daily.merge(card_valid[["CARD", "OBSERVATION DATE"]], on="CARD", suffixes=("", "_start"))
    daily = daily.loc[(daily["OBSERVATION DATE"] >= daily["OBSERVATION DATE_start"])
                      & (daily["OBSERVATION DATE"] < daily["OBSERVATION DATE_start"] + pd.Timedelta(days=5))]
    durations = daily.groupby("CARD")["DURATION MINUTES"].sum().rename("DURATION MINUTES_sum")
    qualified = chk_card.loc[qualifies_effort(chk_card)].copy()
    qualified["EFFORT END"] = qualified["OBSERVATION DATETIME"] + pd.to_timedelta(qualified["DURATION MINUTES"], unit="m")
    ends = qualified.groupby("CARD")["EFFORT END"].max().rename("OBSERVATION DATETIME_max")
    # Any missing distance makes the full total unknown, rather than a partial sum.
    distances = qualified.groupby("CARD")["EFFORT DISTANCE KM"].agg(lambda values: values.sum() if values.notna().all() else np.nan).rename("EFFORT DISTANCE KM_sum")
    # Overlapping route distances cannot be corrected from clocks alone.
    naive = qualified.groupby("CARD")["DURATION MINUTES"].sum()
    overlap = naive.sub(durations).clip(lower=0).rename("OVERLAP MINUTES REMOVED")
    distances.loc[overlap.gt(0) & distances.ne(0)] = np.nan
    card_chk = card_chk.merge(durations, on="CARD").merge(ends, on="CARD").merge(distances, on="CARD").merge(overlap, on="CARD")
    card_chk = card_chk.merge(card_valid, on="CARD", validate="one_to_one")
    last_start = chk_card.groupby("CARD")["OBSERVATION DATETIME"].max()
    card_chk["OBSERVATION DATETIME_max"] = pd.concat([card_chk.set_index("CARD")["OBSERVATION DATETIME_max"], last_start], axis=1).max(axis=1).reindex(card_chk["CARD"]).to_numpy()
    card_chk["OBSERVATION DATETIME_max"] = card_chk["OBSERVATION DATETIME_max"].where(
        card_chk["OBSERVATION DATETIME_max"] < card_chk["OBSERVATION DATE"] + pd.Timedelta(days=5),
        card_chk["OBSERVATION DATE"] + pd.Timedelta(days=5) - pd.Timedelta(microseconds=1))
    return card_chk


def chk_card2ebd_f_u(ebd, chk_card):
    # Filter the full dataset to get only the checklist used in the card data
    ebd_f = ebd.loc[
        ebd["SAMPLING EVENT IDENTIFIER"].isin(chk_card["SAMPLING EVENT IDENTIFIER"]),
        [
            "SAMPLING EVENT IDENTIFIER",
            "SCIENTIFIC NAME",
            "TAXON CONCEPT ID",
            "AVIBASE ID",
            "AVILIST COMMON NAME",
            "AVILIST SCIENTIFIC NAME",
            "AVILIST MATCH",
            "AVILIST VERSION",
            "EBIRD TAXONOMY VERSION",
            "TARGET EBIRD TAXONOMY VERSION",
            "OBSERVATION DATETIME",
            "LATITUDE",
            "LONGITUDE",
            "EFFORT DISTANCE KM",
        ],
    ]

    # Attach the card key.
    ebd_f = pd.merge(
        ebd_f,
        chk_card.loc[:, ["SAMPLING EVENT IDENTIFIER", "CARD"]],
        on="SAMPLING EVENT IDENTIFIER",
        how="left",
    )

    # Keep unresolved concepts under their original keys; never group them
    # under a missing ID or infer a parent species from their names.
    if ebd_f["AVIBASE ID"].isna().any():
        raise ValueError("Cannot export observations with missing Avibase concept IDs; inspect the taxonomy report")

    # Deduplicate by source concept, not scientific-name spelling.
    ebd_f = ebd_f.sort_values("OBSERVATION DATETIME", kind="stable")

    ebd_f_u = ebd_f.drop_duplicates(
        subset=["CARD", "AVIBASE ID"], keep="first"
    ).copy()
    ebd_f_u = ebd_f_u.reset_index(drop=True)

    ebd_f_u["SEQ"] = ebd_f_u.groupby("CARD").cumcount() + 1

    # Convert datetime to standard format
    ebd_f_u["OBSERVATION DATETIME"] = ebd_f_u["OBSERVATION DATETIME"].dt.strftime(
        "%Y-%m-%dT%H:%M:%S"
    )

    return ebd_f_u


def ebd_f_u2card_exp(card_chk, ebd_f_u, *,
                    observer_email=None, observer_no=None):
    """Format resolved species and card metadata; times remain local and timezone-naive."""

    # Extract the species list per card as a cell for vectorized computation
    card_sp = (
        ebd_f_u.groupby("CARD")[
            [
                "SCIENTIFIC NAME",
                "AVIBASE ID",
                "AVILIST COMMON NAME",
                "AVILIST SCIENTIFIC NAME",
                "AVILIST MATCH",
                "AVILIST VERSION",
                "EBIRD TAXONOMY VERSION",
                "TARGET EBIRD TAXONOMY VERSION",
                "SEQ",
                "LATITUDE",
                "LONGITUDE",
                "OBSERVATION DATETIME",
                "EFFORT DISTANCE KM",
            ]
        ]
        .agg(list)
        .reset_index()
    )

    # Merge the card information by checklist and species into an export card dataframe
    card_exp = pd.merge(
        card_chk,
        card_sp,
        on="CARD",
    )

    # Set some default values
    card_exp["Protocol"] = "F"
    card_exp["ValidationStatus"] = "candidate"
    card_exp["SpatialValidation"] = "screen_only"
    card_exp["ObserverEmail"] = observer_email
    card_exp["ObserverNo"] = None if observer_no is None else str(observer_no)

    card_exp["Hour1"] = ""
    card_exp["Hour2"] = ""
    card_exp["Hour3"] = ""
    card_exp["Hour4"] = ""
    card_exp["Hour5"] = ""
    card_exp["Hour6"] = ""
    card_exp["Hour7"] = ""
    card_exp["Hour8"] = ""
    card_exp["Hour9"] = ""
    card_exp["Hour10"] = ""
    card_exp["InclNight"] = None
    card_exp["AllHabitats"] = None

    card_exp["TotalHours"] = round(card_exp["DURATION MINUTES_sum"] / 60, 2)
    card_exp["TotalDistance"] = round(card_exp["EFFORT DISTANCE KM_sum"], 2)
    card_exp["TotalSpp"] = card_exp["AVIBASE ID"].apply(lambda x: len(x))
    card_exp["StartDate"] = card_exp["OBSERVATION DATETIME_min"].dt.date.apply(str)
    card_exp["EndDate"] = card_exp["OBSERVATION DATETIME_max"].dt.date.apply(str)
    card_exp["StartTime"] = card_exp["OBSERVATION DATETIME_min"].dt.strftime("%H:%M")

    # Function that generate species record to be used for each species of each card
    def create_records(
        SCIENTIFIC_NAME,
        AVIBASE_ID,
        AVILIST_COMMON_NAME,
        AVILIST_SCIENTIFIC_NAME,
        SEQ,
        LATITUDE,
        LONGITUDE,
        OBSERVATION_DATETIME,
        EFFORT_DISTANCE_KM,
        TAXONOMY_STATUS,
        AVILIST_VERSION,
        EBIRD_SOURCE_VERSION,
        EBIRD_TARGET_VERSION,
        CARD,
    ):
        return [
            {
                "Sequence": None,
                "RecordIndex": SEQ,
                "SightingTimeBasis": "checklist_start",
                "Latitude": LATITUDE,
                "Longitude": LONGITUDE,
                "Altitude": "",
                "CardNo": CARD,
                "Spp": AVIBASE_ID,
                "SourceSpp": SCIENTIFIC_NAME,
                "CommonName": AVILIST_COMMON_NAME,
                "ScientificName": AVILIST_SCIENTIFIC_NAME,
                "TaxonomyStatus": TAXONOMY_STATUS,
                "AviListVersion": AVILIST_VERSION,
                "eBirdSourceTaxonomyVersion": EBIRD_SOURCE_VERSION,
                "eBirdTargetTaxonomyVersion": EBIRD_TARGET_VERSION,
                "Accuracy": None,
                "SightingTime": OBSERVATION_DATETIME,
            }
            for SCIENTIFIC_NAME, AVIBASE_ID, AVILIST_COMMON_NAME, AVILIST_SCIENTIFIC_NAME, SEQ, LATITUDE, LONGITUDE, OBSERVATION_DATETIME, EFFORT_DISTANCE_KM, TAXONOMY_STATUS, AVILIST_VERSION, EBIRD_SOURCE_VERSION, EBIRD_TARGET_VERSION in zip(
                SCIENTIFIC_NAME,
                AVIBASE_ID,
                AVILIST_COMMON_NAME,
                AVILIST_SCIENTIFIC_NAME,
                SEQ,
                LATITUDE,
                LONGITUDE,
                OBSERVATION_DATETIME,
                EFFORT_DISTANCE_KM,
                TAXONOMY_STATUS,
                AVILIST_VERSION,
                EBIRD_SOURCE_VERSION,
                EBIRD_TARGET_VERSION,
            )
        ]

    # Apply the function
    card_exp["records"] = pd.Series(dtype=object) if card_exp.empty else card_exp.apply(
        lambda row: create_records(
            row["SCIENTIFIC NAME"],
            row["AVIBASE ID"],
            row["AVILIST COMMON NAME"],
            row["AVILIST SCIENTIFIC NAME"],
            row["SEQ"],
            row["LATITUDE"],
            row["LONGITUDE"],
            row["OBSERVATION DATETIME"],
            row["EFFORT DISTANCE KM"],
            row["AVILIST MATCH"],
            row["AVILIST VERSION"],
            row["EBIRD TAXONOMY VERSION"],
            row["TARGET EBIRD TAXONOMY VERSION"],
            row["CARD"],
        ),
        axis=1,
    )

    # Rename to match ABAP server input
    card_exp = card_exp.rename(
        columns={
            "CARD": "CardNo",
            "PENTAD": "Pentad",
            "SAMPLING EVENT IDENTIFIER": "Checklists",
            "OBSERVER ID": "ObserverNoEbird",
            "SAMPLING EVENT IDENTIFIER_list": "Checklists",
            "SOURCE CHECKLIST IDS": "SourceChecklists",
            "SOURCE OBSERVER IDS": "SourceObservers",
            "EVENT IDS": "Events",
            "OVERLAP MINUTES REMOVED": "OverlapMinutesRemoved",
        }
    )

    card_exp = card_exp.reindex(
        columns=[
            "Protocol",
            "ValidationStatus",
            "SpatialValidation",
            "SourceChecklists",
            "SourceObservers",
            "Events",
            "OverlapMinutesRemoved",
            "ObserverEmail",
            "CardNo",
            "StartDate",
            "EndDate",
            "StartTime",
            "Pentad",
            "ObserverNo",
            "TotalHours",
            "Hour1",
            "Hour2",
            "Hour3",
            "Hour4",
            "Hour5",
            "Hour6",
            "Hour7",
            "Hour8",
            "Hour9",
            "Hour10",
            "TotalSpp",
            "InclNight",
            "AllHabitats",
            "Checklists",
            "TotalDistance",
            "ObserverNoEbird",
            "records",
        ]
    )

    return card_exp
