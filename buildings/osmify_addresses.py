import pandas as pd

import geopandas as gpd
import osmnx as ox

FILENAME = "Parcel_Address"
IN_FILENAME = FILENAME + ".csv"
OUT_FILENAME = FILENAME + ".geojson"


overpass_url = "http://overpass-api.de/api/interpreter"

def fetch_street_names():
    osm = ox.features_from_place(
        "Calgary, Alberta, Canada",
        {
            "highway": [
                "motorway",
                "motorway_link",
                "primary",
                "primary_link",
                "secondary",
                "secondary_link",
                "tertiary",
                "tertiary_link",
                "residential",
                "unclassified",
                "service",
                "living_street",
            ]
        },
    )
    # filter out streets without name
    osm = osm[osm["name"].notnull()]
    osm = osm.loc[osm.index.get_level_values("element") == "way"]
    sorted_streets = sorted(osm["name"].unique())
    return sorted_streets


osm_street_names = fetch_street_names()
# print(len(osm_street_names), "street names")
for name in osm_street_names:
    if name.rsplit(" ", 1)[-1] not in ["SW", "SE", "NW", "NE"] and name not in [
        "Centre Street S",
        "Centre Street N",
        # "Centre Avenue E",
    ]:
        # print(name)
        pass


# https://data.calgary.ca/Base-Maps/Parcel-Address/9zvu-p8uz/about_data
street_types = {
    "AL": "Alley",
    "AV": "Avenue",
    "BA": "Bay",
    "BV": "Boulevard",
    "CA": "Cape",
    "CE": "Centre",
    "CI": "Circle",
    "CL": "Close",
    "CM": "Common",
    "CO": "Court",
    "CR": "Crescent",
    "CV": "Cove",
    "DR": "Drive",
    "GA": "Gate",
    "GD": "Gardens",
    "GR": "Green",
    "GV": "Grove",
    "HE": "Heath",
    "HI": "Highway",
    "HL": "Hill",
    "HT": "Heights",
    "IS": "Island",
    "LD": "Landing",
    "LI": "Link",
    "LN": "Lane",
    "ME": "Mews",
    "MR": "Manor",
    "MT": "Mount",
    "PA": "Park",
    "PH": "Path",
    "PL": "Place",
    "PR": "Parade",
    "PS": "Passage",
    "PT": "Point",
    "PY": "Parkway",
    "PZ": "Plaza",
    "RD": "Road",
    "RI": "Rise",
    "RO": "Row",
    "SQ": "Square",
    "ST": "Street",
    "TC": "Terrace",
    "TR": "Trail",
    "VI": "Villas",
    "VW": "View",
    "WK": "Walk",
    "WY": "Way",
}


# df = pd.read_csv("Parcel_Address_20250127.csv", nrows=200)
df = pd.read_csv(IN_FILENAME)
# print(df.columns)

if not all(df["ADDRESS_TYPE"] == "Parcel"):
    raise ValueError("Not all ADDRESS_TYPE is 'Parcel'", df["ADDRESS_TYPE"].unique())
# df.drop(columns=["ADDRESS", "ADDRESS_TYPE", "location", "POINT"], inplace=True)
# print(df.head())

if df["STREET_QUAD"].isnull().any():
    raise ValueError("STREET_QUAD has NaNs")
if df["STREET_TYPE"].isnull().any():
    raise ValueError("STREET_TYPE has NaNs")
if df["STREET_NAME"].isnull().any():
    raise ValueError("STREET_NAME has NaNs")
if df["HOUSE_NUMBER"].isnull().any():
    raise ValueError("HOUSE_NUMBER has NaNs")


# check that STREET_QUAD is "SW", "SE", "NW", "NE"
if not all(df["STREET_QUAD"].isin(["SW", "SE", "NW", "NE"])):
    raise ValueError(
        "STREET_QUAD is not 'SW', 'SE', 'NW', 'NE'", df["STREET_QUAD"].unique()
    )

# check all STREE_TYPE is in street_types
if not all(df["STREET_TYPE"].isin(street_types.keys())):
    diff = set(df["STREET_TYPE"].unique()) - street_types.keys()
    raise ValueError(
        "STREET_TYPE is not in street_types: " + ", ".join(list(sorted(list((diff)))))
    )
# print(df["STREET_TYPE"].value_counts())
# Expand street abbreviations
df["STREET_TYPE"] = df["STREET_TYPE"].map(street_types)


# print(df["HOUSE_ALPHA"].unique())
# print("\n".join(list(df[df["HOUSE_ALPHA"].notnull()]["ADDRESS"])))
df.rename(
    {"HOUSE_NUMBER": "addr:housenumber", "HOUSE_ALPHA": "addr:unit"},
    axis=1,
    inplace=True,
)
# TODO: or should it be joined?
# df["addr:housenumber"] = df["HOUSE_NUMBER"].astype(str) + df["HOUSE_ALPHA"].astype(str).replace("nan", "")
# df.drop(columns=["HOUSE_NUMBER", "HOUSE_ALPHA"], inplace=True)

for i, name in enumerate(df["STREET_NAME"]):
    if name.startswith("ST "):
        if name.startswith("ST MORITZ"):
            df.at[i, "STREET_NAME"] = "St. Moritz" + name[len("ST MORITZ") :]
        elif name.startswith("ST MONICA"):
            df.at[i, "STREET_NAME"] = "St. Monica" + name[len("ST MONICA") :]
        else:
            df.at[i, "STREET_NAME"] = "Saint " + name[3:]
    elif name.startswith("TWELVE MI COULEE"):
        name = name.replace("TWELVE MI COULEE", "Twelve Mile Coulee")
    if name.startswith("MT "):
        df.at[i, "STREET_NAME"] = "Mount " + name[3:]
df["addr:street"] = (
    df["STREET_NAME"].str.title() + " " + df["STREET_TYPE"] + " " + df["STREET_QUAD"]
)

# df.drop(["longitude", "latitude"], axis=1, inplace=True)
df.drop(
    [
        "ADDRESS",
        "ADDRESS_TYPE",
        "location",
        "POINT",
        "STREET_NAME",
        "STREET_TYPE",
        "STREET_QUAD",
    ],
    axis=1,
    inplace=True,
)

gdf = gpd.GeoDataFrame(
    df, geometry=gpd.points_from_xy(df["longitude"], df["latitude"]), crs="EPSG:4326"
)
gdf.drop(
    columns=[
        "longitude",
        "latitude",
        # "STREET_NAME",
        # "STREET_TYPE",
        # "STREET_QUAD",
    ],
    inplace=True,
)
# gdf.to_file(FILENAME + "_osm.geojson", driver="GeoJSON")


osm_names = {
    "centre street ne": "Centre Street NE",
    "centre street nw": "Centre Street NW",
    "centre street se": "Centre Street SE",
    "centre street sw": "Centre Street SW",
    "centre avenue ne": "Centre Avenue NE",
    "centre avenue nw": "Centre Avenue NW",
    "centre avenue se": "Centre Avenue SE",
    "centre avenue sw": "Centre Avenue SW",
    "harvest hills boulevard ne": "Harvest Hills Boulevard NE",
    "harvest hills boulevard nw": "Harvest Hills Boulevard NW",
    "trans canada highway sw": "Trans-Canada Highway SW",
    "trans canada highway nw": "Trans-Canada Highway NW",
    "metis trail ne": "Métis Trail NE",
    "metis trail nw": "Métis Trail NW",
}
for name in osm_street_names:
    # Remove numeric prefixes from names
    for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 30, 40]:
        prefix = f"{i}00 "
        if name.startswith(prefix) and not (
            name.startswith(prefix + "Avenue ") or name.startswith(prefix + "Street ")
        ):
            name = name[len(prefix) :]
    if name.lower() in osm_names and osm_names[name.lower()] != name:
        print(name)
        print(osm_names[name.lower()])
        print()
        pass
    osm_names[name.lower()] = name

coc = set(df["addr:street"].str.lower())
osm = set(osm_names.keys())
missing = coc - osm
# print("coc:", len(coc))
# print("osm:", len(osm))
# print("in coc, not in osm:", len(coc - osm))
# save those to file as geojson
not_in = df[df["addr:street"].str.lower().isin(missing)].copy()
gdf = gpd.GeoDataFrame(
    not_in, geometry=gpd.points_from_xy(not_in["longitude"], not_in["latitude"])
)
gdf.drop(["longitude", "latitude"], axis=1, inplace=True)
gdf.set_crs("EPSG:4326", inplace=True)
gdf.to_file(FILENAME + "_not_in_osm.geojson", driver="GeoJSON")

in_osm = df[df["addr:street"].str.lower().isin(osm)].copy()
in_osm["addr:street"] = in_osm["addr:street"].str.lower().map(osm_names)
gdf = gpd.GeoDataFrame(
    in_osm, geometry=gpd.points_from_xy(in_osm["longitude"], in_osm["latitude"])
)
gdf.drop(["longitude", "latitude"], axis=1, inplace=True)
gdf.set_crs("EPSG:4326", inplace=True)
gdf.to_file(FILENAME + "_osm.geojson", driver="GeoJSON")
