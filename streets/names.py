# Gets street names from OpenStreetMap and City of Calgary data
# and compares them to find streets that are in one but not the other
# and vice versa.
# Outputs two GeoJSON files: osm_not_in_coc.geojson and coc_not_in_osm.geojson

import sys
import difflib

import geopandas as gpd
import osmnx as ox


COC_FILENAME = "Street Centreline.geojson"

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

# load Street Centreline.geojson file
coc = gpd.read_file(COC_FILENAME)
# filter out streets without name or octant
coc = coc[(coc["name"].notnull()) & (coc["octant"].notnull())]
# print(coc.columns)
# print(coc.head())


def to_osm_name(row):
    name = (
        row["name"].title()
        + " "
        + street_types[row["street_type"]]
        + " "
        + row["octant"]
    )
    if name.startswith("Suncanyon "):
        name = "Sun Canyon " + name[len("Suncanyon ") :]
    if name.startswith("Mt "):
        name = "Mount " + name[len("Mt ") :]
    name = name.replace(" Mt ", " Mount ")
    if row["numeric_preface"]:
        name = row["numeric_preface"] + " " + name
    return name


def coc_special_cases(name):
    if name.startswith("martha's "):
        name = "marthas " + name[len("martha's ") :]
    if name == "twelve mi coulee road nw":
        name = "twelve mile coulee road nw"
    if name.startswith("st georges "):
        name = "st george's " + name[len("st georges ") :]
    if "trans canada hi" in name:
        name = "trans-canada highway"
    return name


coc["osm_name"] = coc.apply(to_osm_name, axis=1)
coc["join_key"] = coc["osm_name"].str.lower().apply(coc_special_cases)


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
osm.to_file("osm_streets.geojson", driver="GeoJSON")
osm = osm[["name", "geometry", "highway"]]
# print(osm.columns)
# print(osm.head())

print("Loaded data", len(coc), len(osm), file=sys.stderr)

quads = {
    "southwest": "sw",
    "southeast": "se",
    "northwest": "nw",
    "northeast": "ne",
    "south-west": "sw",
    "south-east": "se",
    "north-west": "nw",
    "north-east": "ne",
}


def osm_name_to_join_key(name):
    # for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 30, 40]:
    #     prefix = f"{i}00 "
    #     if name.startswith(prefix) and name.split()[1] not in ["Street", "Avenue"]:
    #         name = name[len(prefix) :]
    #         break
    name = name.lower()
    if name.startswith("saint "):
        name = "st " + name[len("saint ") :]
    if name.startswith("st. "):
        name = "st " + name[len("st. ") :]
    name = name.replace(" st. ", " st ")
    if name.startswith("dr. "):
        name = "dr " + name[len("dr. ") :]
    if name.startswith("métis "):
        name = "metis " + name[len("métis ") :]
    # TODO: remove this
    if name.startswith("martha's "):
        name = "marthas " + name[len("martha's ") :]
    for longquad, quad in quads.items():
        if name.endswith(f" {longquad}"):
            name = name[: -len(longquad)] + quad
            break
    if name == "tsuut'ina trail":
        name = "tsuut'ina trail sw"
    return name.lower()


osm["join_key"] = osm["name"].apply(osm_name_to_join_key)


joined = coc.merge(osm, on="join_key", how="left", suffixes=("_coc", "_osm"))

# save just the rows in osm_named_streets.geojson that are not in the joined dataframe
osm_not_in_coc = osm[~osm["join_key"].isin(joined["join_key"])]
osm_not_in_coc.to_file("osm_not_in_coc.geojson", driver="GeoJSON")

# do it the other way around and
# save just the rows in Street Centreline_20250225.geojson that are not in the joined dataframe
joined = osm.merge(coc, on="join_key", how="left", suffixes=("_osm", "_coc"))
coc_not_in_osm = coc[~coc["join_key"].isin(joined["join_key"])]
coc_not_in_osm.to_file("coc_not_in_osm.geojson", driver="GeoJSON")

osm_keys = set(osm_not_in_coc["join_key"])
coc_keys = set(coc_not_in_osm["join_key"])

print(f"{len(osm_keys)} OSM keys not in CoC", file=sys.stderr)
for key in sorted(osm_keys):
    name = osm[osm["join_key"] == key].iloc[0]["name"]
    # find the closest match in coc_keys
    closest = difflib.get_close_matches(key, coc_keys, n=3)
    print(f"{name} ({key})", file=sys.stderr)
    for c in closest:
        c_name = coc[coc["join_key"] == c].iloc[0]["osm_name"]
        print(f"    {c_name} ({c})", file=sys.stderr)


print()
print(f"{len(coc_keys)} CoC keys not in OSM", file=sys.stderr)
for key in sorted(coc_keys):
    name = coc[coc["join_key"] == key].iloc[0]["osm_name"]
    # find the closest match in coc_keys
    closest = difflib.get_close_matches(key, osm_keys, n=3)
    print(f"{name} ({key})", file=sys.stderr)
    for c in closest:
        c_name = osm[osm["join_key"] == c].iloc[0]["name"]
        print(f"    {c_name} ({c})", file=sys.stderr)
