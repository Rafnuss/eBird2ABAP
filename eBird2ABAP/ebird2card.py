import pandas as pd
import numpy as np
import importlib.resources as pkg_resources

# import json
import os
import datetime

import requests
import tarfile

# from tqdm.notebook import tqdm

# import sys
# import csv

# Now import the necessary functions from utils.py
from .utils import latlng2pentad, pentad2latlng


def ebird2abap(EBD_file, JSON_file=None, exportCSV=False):
    print("Reading EBD file...")
    ebd = read_EBD(EBD_file)

    print("Adding ADU number...")
    ebd = add_ADU(ebd)

    print("Computing checklists...")
    chk = ebd2chk(ebd)

    print("Checking validity of cards...")
    card_valid = chk2valid_card(chk)

    print("Converting valid cards to CHK cards...")
    chk_card = valid_card2chk_card(chk, card_valid)

    print("Converting CHK cards to card check...")
    card_chk = chk_card2card_chk(chk_card, card_valid)

    print("Converting CHK cards to EBD formatted units...")
    ebd_f_u = chk_card2ebd_f_u(ebd, chk_card)

    print("Converting EBD formatted units to card expressions...")
    card_exp = ebd_f_u2card_exp(card_chk, ebd_f_u)

    print("Converting card expressions to JSON format...")
    json_data = card_exp.to_json(orient="records", indent=2)

    if JSON_file is None:
        basename = (
            os.path.basename(EBD_file).removesuffix(".txt.gz").removesuffix(".txt")
        )
        JSON_file = (
            f"{basename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )

    print(f"Writing JSON data to {JSON_file}...")
    with open(JSON_file, "w") as f:
        f.write(json_data)

    if exportCSV:
        print(f"Writing CSV data...")
        card_chk.to_csv(
            f"{basename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_cards.csv",
            index=False,
        )
        ebd_f_u[["CARD", "ADU", "SEQ"]].to_csv(
            f"{basename}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_records.csv",
            index=False,
        )

    print("Process completed successfully.")


def download_EBD(year=None, month=None):
    if (year is None) | (month is None):
        # Calculate previous month and year
        today = datetime.date.today()
        last_month = today.replace(day=1) - datetime.timedelta(days=1)
        if year is None:
            year = last_month.strftime("%Y")
        if month is None:
            month = last_month.strftime("%b")

    # Construct URL and filename
    url = f"https://download.ebird.org/ebd/prepackaged/ebd_AFR_rel{month}-{year}.tar"
    filename = os.path.basename(url)
    filepath = os.path.join("../data/eBird/", filename)

    with open(filepath, "wb") as f:
        print(f"Request data at {url}")
        f.write(requests.get(url).content)

    with tarfile.open(filepath, "r") as tar:
        tar.extractall(f"../data/eBird/ebd_AFR_rel{month}-{year}/")

    return filepath


def read_EBD(file, nrows=None):
    ebd0 = pd.read_csv(
        file,
        delimiter="\t",
        usecols=[
            "SAMPLING EVENT IDENTIFIER",
            "GROUP IDENTIFIER",
            "SCIENTIFIC NAME",
            "TAXON CONCEPT ID",
            "CATEGORY",
            "LATITUDE",
            "LONGITUDE",
            "OBSERVATION DATE",
            "TIME OBSERVATIONS STARTED",
            "PROTOCOL TYPE",
            "DURATION MINUTES",
            "EFFORT DISTANCE KM",
            "ALL SPECIES REPORTED",
            "OBSERVER ID",
        ],
        parse_dates=["OBSERVATION DATE"],
        nrows=nrows,  # Use this to read only a smaller portion of the file to run faster and test the code
    )

    ebd = ebd0

    # Combine shared checklist: Overwrite sampling event identifier by the first one submitted (lower SXXXXXX value)
    ebd["SAMPLING EVENT IDENTIFIER"] = (
        ebd.groupby("GROUP IDENTIFIER")["SAMPLING EVENT IDENTIFIER"]
        .transform("min")
        .where(ebd["GROUP IDENTIFIER"].notna(), ebd["SAMPLING EVENT IDENTIFIER"])
    )
    # Drop the GROUP IDENTIFIER column
    ebd = ebd.drop(columns="GROUP IDENTIFIER")

    # Create OBSERVATIONDATETIME by combining date and time
    tmp = ebd["TIME OBSERVATIONS STARTED"].fillna("00:00:00")
    ebd["OBSERVATION DATETIME"] = pd.to_datetime(
        ebd["OBSERVATION DATE"].dt.strftime("%Y-%m-%d") + " " + tmp,
        format="%Y-%m-%d %H:%M:%S",
    )

    # Sort by date: Important to have for filtering duplicate card-adu and needed for sequence
    ebd.sort_values(by="OBSERVATION DATETIME", inplace=True)

    # Keep only species category
    # ebd0[["COMMONNAME", "SCIENTIFIC NAME", "CATEGORY"]].drop_duplicates().to_csv("species_list_ebird.csv", index=False)

    # Keep some spuh which can be matched to an ADU
    # spuh_keep = pd.read_csv("data/spuh_keep.csv", dtype=str)
    # ebd0 = ebd0[(~ebd0["CATEGORY"].isin(["spuh", "slash"])) | ebd0["SCIENTIFIC NAME"].isin(spuh_keep["Clements--scientific_name"])]

    return ebd


def load_matched_species():
    with pkg_resources.files("eBird2ABAP").joinpath("matched_species.csv") as file_path:
        print(file_path)
        df = pd.read_csv(file_path)
    return df


def add_ADU(ebd, return_unmatched=False):
    # Read matched_species data. See species_match.ipynb
    matched_species = load_matched_species()

    ebd = pd.merge(
        ebd,  # .loc[:,['OBSERVER ID', 'PENTAD', "SAMPLING EVENT IDENTIFIER", "OBSERVATION DATE"]],
        matched_species[["TAXON CONCEPT ID", "ADU"]].drop_duplicates(
            subset="TAXON CONCEPT ID"
        ),
        how="left",
    )

    if return_unmatched:
        unmatched = (
            ebd[ebd["ADU"].isna()][["SCIENTIFIC NAME"]]
            .value_counts()
            .sort_values(ascending=0)
        )
        print(
            f"We still have {len(unmatched)} unmatched taxons, corresponding to {round(sum(unmatched)/len(ebd)*100)}% of our data"
        )
        return unmatched
    else:
        ebd["ADU"] = ebd["ADU"].fillna(0).astype(int)
        return ebd


def ebd2chk(ebd):
    chk = ebd[
        [
            "SAMPLING EVENT IDENTIFIER",
            "LATITUDE",
            "LONGITUDE",
            "OBSERVATION DATE",
            "OBSERVATION DATETIME",
            "PROTOCOL TYPE",
            "DURATION MINUTES",
            "EFFORT DISTANCE KM",
            "ALL SPECIES REPORTED",
            "OBSERVER ID",
        ]
    ].drop_duplicates()

    # Sort by date
    chk.sort_values(by="OBSERVATION DATETIME", inplace=True)

    # For some shared checklist some variable are different for the same sampling event.
    # chk[chk["SAMPLING EVENT IDENTIFIER"].duplicated(keep=False)].sort_values(by="SAMPLING EVENT IDENTIFIER")
    # ebd0[ebd0["SAMPLING EVENT IDENTIFIER"] == "S97700871"]
    chk = chk.drop_duplicates("SAMPLING EVENT IDENTIFIER").reset_index(drop=True)
    len(chk)

    # Filter protocol
    chk["KEEP PROTOCOL"] = chk["PROTOCOL TYPE"].isin(
        ["Historical", "Incidental", "Stationary", "Traveling"]
    )

    # Pentad
    # Assign the pentad to all checklists based on their location
    chk["PENTAD"] = latlng2pentad(chk["LATITUDE"], chk["LONGITUDE"])

    # Retrieve the lat, lon center of the assigned pentad
    lat, lon = pentad2latlng(chk["PENTAD"])

    # Convert effort distance of the checklisst into degree lat-lon
    effort_distance_lat = 180 / np.pi / 6371 * chk["EFFORT DISTANCE KM"]
    effort_distance_lon = (
        180
        / np.pi
        / 6371
        / np.cos(np.radians(chk["LATITUDE"]))
        * chk["EFFORT DISTANCE KM"]
    )

    # Compute the distance from the center of the pentad (lat,lon) to the max distance possible if the observer traveled in the worst possible direction (i.e., to the closest eadge of the pentad)
    # We relax a little bit the assumption of moving on the straight line to the edge of the pentad by applying a correction factor
    corr_straight_line = 0.8
    dist_lat = np.abs(lat - chk["LATITUDE"]) + effort_distance_lat * corr_straight_line
    dist_lon = np.abs(lon - chk["LONGITUDE"]) + effort_distance_lon * corr_straight_line

    # The maximum distance allowed for the checklist to be considered valid is half of a pentad resolution (5/60°)
    # We accept that the checklist might have traveled a bit more that this distance
    corr_overlap = 1.2  # allow for a 20% overlap
    max_dist = (5 / 60 / 2) * corr_overlap

    chk["KEEP PENTAD"] = (dist_lat < max_dist) & (dist_lon < max_dist)

    # Filter historical checklists which have no distance
    chk.loc[
        (chk["PROTOCOL TYPE"] == "Historical") & chk["EFFORT DISTANCE KM"].isna(),
        "KEEP PENTAD",
    ] = False

    # Filter historical checklists which have no distance
    chk.loc[
        chk["EFFORT DISTANCE KM"].isna(),
        "KEEP PENTAD",
    ] = True

    chk.loc[
        (chk["PROTOCOL TYPE"] == "Historical") & chk["EFFORT DISTANCE KM"].isna(),
        "KEEP PENTAD",
    ] = False

    return chk


def chk2valid_card(chk):
    # Find all possible valid card
    # Cards are considered to be full protocol if the sum of durations of the underlying checklists exceed 2 hours over the next rolling 5 days.
    # In this section, we first indentify which checklists can create a valid full card.

    # Find the index of all checklists which contribute to the 2hr rule. Note that we will still use "non-valid" checklists later as their species still contribute to the card.
    valid_id = (
        chk["KEEP PENTAD"]
        & chk["KEEP PROTOCOL"]
        & (chk["DURATION MINUTES"] > 0)
        & chk["ALL SPECIES REPORTED"]
    )

    # Filter for valid checklist and create in a smaller table
    check = chk.loc[
        valid_id, ["PENTAD", "OBSERVER ID", "OBSERVATION DATE", "DURATION MINUTES"]
    ]

    # Combine checklists made by the same observer, pentad, and day. This is an intermediate step which enables us to grid the 5 days windows more easily
    checkday = (
        check.groupby(["PENTAD", "OBSERVER ID", "OBSERVATION DATE"])
        .agg({"DURATION MINUTES": "sum"})
        .reset_index()
    )

    # Sort the checklist by date
    checkday.sort_values(by=["OBSERVATION DATE"], inplace=True)

    # Create additional columns
    checkday["pentad_observer"] = checkday["PENTAD"] + "_" + checkday["OBSERVER ID"]
    checkday["pentad_observer_date"] = (
        checkday["PENTAD"]
        + "_"
        + checkday["OBSERVER ID"].str[3:]
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

    # Second filter for reducing the test case
    # pentad_observer_unique = checkday_long["pentad_observer"].unique()
    # pentad_observer_unique = pentad_observer_unique[0:1000]
    # checkday_long = checkday_long[checkday_long["pentad_observer"].isin(pentad_observer_unique)]

    # Apply the function defined above for each pentad-observer at the same time (makes operation much faster)
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
    card_valid.sort_values(by="CARD", inplace=True)

    return card_valid


# To find all pentad with sufficient duration effort (i.e, a sum of 2h over 5 days period), we apply this function for each pentad_observer.
def checkday_pentad_observer(df):
    df["CARD"] = ""
    # Build a matrix of distance between all checklists to check if they are close to each other
    di = np.abs(
        df["OBSERVATION DATE"].values[:, None] - df["OBSERVATION DATE"].values
    ) < pd.Timedelta(days=5)
    # create duration array to make computation slightly faster
    duration = df["DURATION MINUTES"].to_numpy()
    # Initie the card array with empty string
    # card = np.array(['' for x in range(len(df))], dtype='object')
    u = 1
    # Loop trough the list of checklists
    while u <= len(df):
        # Find all neighbord
        nb_neighbor = np.sum(di[u - 1, (u - 1) :])
        neigh = u + np.arange(0, nb_neighbor) - 1
        dur = duration[neigh].sum()
        # Check that total duration is more than 2hours, if so add card code (pentad_observer_date) to card array
        if dur >= (2 * 60):
            df.iloc[neigh, df.columns.get_loc("CARD")] = df.iloc[
                u - 1, df.columns.get_loc("pentad_observer_date")
            ]
        u += nb_neighbor
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
    chk_card = chk_card[(duration >= 0) & (duration < 5)]

    return chk_card


def chk_card2card_chk(chk_card, card_valid):

    # Cretate the card list with all checklists that belong to it. Compute aggregated value of all checklists
    card_chk = (
        chk_card.groupby("CARD")
        .agg(
            {
                "SAMPLING EVENT IDENTIFIER": list,
                "OBSERVATION DATETIME": ["min", "max"],
                "DURATION MINUTES": "sum",
                "EFFORT DISTANCE KM": "sum",
            }
        )
        .reset_index()
    )
    card_chk.columns = ["_".join(col).strip("_") for col in card_chk.columns.values]

    # merge with the information contained in card_valid
    card_chk = pd.merge(card_chk, card_valid, on="CARD", how="inner")

    return card_chk


def chk_card2ebd_f_u(ebd, chk_card):
    # Filter the full dataset to get only the checklist used in the card data
    ebd_f = ebd.loc[
        ebd["SAMPLING EVENT IDENTIFIER"].isin(chk_card["SAMPLING EVENT IDENTIFIER"]),
        [
            "SAMPLING EVENT IDENTIFIER",
            "SCIENTIFIC NAME",
            "TAXON CONCEPT ID",
            "ADU",
            "OBSERVATION DATETIME",
            "LATITUDE",
            "LONGITUDE",
            "EFFORT DISTANCE KM",
        ],
    ]

    # Add card_id
    ebd_f = pd.merge(
        ebd_f,
        chk_card.loc[:, ["SAMPLING EVENT IDENTIFIER", "CARD"]],
        on="SAMPLING EVENT IDENTIFIER",
        how="left",
    )

    # Keep a unique list of card-species (remove duplicate species in the same card, keeping the first one in time)
    ebd_f.sort_values(
        by="OBSERVATION DATETIME", inplace=True
    )  # SHould have been done already above, but necessary for keep="first"

    ebd_f_u = ebd_f.drop_duplicates(
        subset=["CARD", "TAXON CONCEPT ID"], keep="first"
    ).copy()
    ebd_f_u.reset_index(drop=True, inplace=True)

    # Compute the sequence of records based on datetime entry
    # ebd_f_u["SEQ"] = (
    #    ebd_f_u.groupby("CARD")["OBSERVATION DATETIME"].rank(method="min").astype(int)
    # )

    # Compute the sequence basd on taxonomical order
    ebd_f_u["SEQ"] = (
        ebd_f_u.groupby("CARD")["TAXON CONCEPT ID"]
        .rank(method="min")
        .fillna(-1)
        .astype(int)
    )

    # Not sure why, but fillina NA by nothing
    ebd_f_u["EFFORT DISTANCE KM"] = ebd_f_u["EFFORT DISTANCE KM"].fillna("")

    # Convert datetime to standard format
    ebd_f_u["OBSERVATION DATETIME"] = ebd_f_u["OBSERVATION DATETIME"].dt.strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    return ebd_f_u


def ebd_f_u2card_exp(card_chk, ebd_f_u):

    # Extract the species list per card as a cell for vectorized computation
    card_sp = (
        ebd_f_u.groupby("CARD")[
            [
                "TAXON CONCEPT ID",
                "ADU",
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
    card_exp["ObserverEmail"] = "kenyabirdmap@naturekenya.org"
    card_exp["ObserverNo"] = "22829"

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
    card_exp["InclNight"] = "0"
    card_exp["AllHabitats"] = "0"

    card_exp["TotalHours"] = round(card_exp["DURATION MINUTES_sum"] / 60, 2)
    card_exp["TotalDistance"] = round(card_exp["EFFORT DISTANCE KM_sum"], 2)
    card_exp["TotalSpp"] = card_exp["ADU"].apply(lambda x: len(x))
    card_exp["StartDate"] = card_exp["OBSERVATION DATETIME_min"].dt.date.apply(str)
    card_exp["EndDate"] = card_exp["OBSERVATION DATETIME_max"].dt.date.apply(str)
    card_exp["StartTime"] = card_exp["OBSERVATION DATETIME_min"].dt.strftime("%H:%M")

    # Function that generate species record to be used for each species of each card
    def create_records(
        TAXON_CONCEPT_ID,
        ADU,
        SEQ,
        LATITUDE,
        LONGITUDE,
        OBSERVATION_DATETIME,
        EFFORT_DISTANCE_KM,
        CARD,
    ):
        return [
            {
                "Sequence": SEQ,
                "Latitude": LATITUDE,
                "Longitude": LONGITUDE,
                "Altitude": "",
                "CardNo": CARD,
                "Spp": ADU,
                "SourceSpp": TAXON_CONCEPT_ID,
                "Accuracy": EFFORT_DISTANCE_KM * 1000,
                "SightingTime": OBSERVATION_DATETIME,
            }
            for TAXON_CONCEPT_ID, ADU, SEQ, LATITUDE, LONGITUDE, OBSERVATION_DATETIME, EFFORT_DISTANCE_KM in zip(
                TAXON_CONCEPT_ID,
                ADU,
                SEQ,
                LATITUDE,
                LONGITUDE,
                OBSERVATION_DATETIME,
                EFFORT_DISTANCE_KM,
            )
        ]

    # Apply the function
    card_exp["records"] = card_exp.apply(
        lambda row: create_records(
            row["TAXON CONCEPT ID"],
            row["ADU"],
            row["SEQ"],
            row["LATITUDE"],
            row["LONGITUDE"],
            row["OBSERVATION DATETIME"],
            row["EFFORT DISTANCE KM"],
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
        }
    )

    card_exp = card_exp.reindex(
        columns=[
            "Protocol",
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
