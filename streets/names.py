# Gets street names from OpenStreetMap and City of Calgary data
# and compares them to find streets that are in one but not the other
# and vice versa.
# Outputs two GeoJSON files: osm_not_in_coc.geojson and coc_not_in_osm.geojson

import geopandas as gpd


COC_FILENAME = "Street Centreline_20250225.geojson"
# https://overpass-turbo.eu/s/1Zn5
OSM_FILENAME = "streets.geojson"

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

# load Street Centreline_20250225.geojson file
coc = gpd.read_file(COC_FILENAME)
# filter out streets without name or octant
coc = coc[(coc["name"].notnull()) & (coc["octant"].notnull())]
print(coc.columns)
print(coc.head())


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
    if row["numeric_preface"]:
        name = row["numeric_preface"] + " " + name
    return name


coc["osm_name"] = coc.apply(to_osm_name, axis=1)
coc["join_key"] = coc["osm_name"].str.lower().replace("martha's ", "marthas ")


osm = gpd.read_file(OSM_FILENAME)
# filter out streets without name
osm = osm[osm["name"].notnull()]
print(osm.columns)
print(osm.head())

quads = {
    "Southwest": "SW",
    "Southeast": "SE",
    "Northwest": "NW",
    "Northeast": "NE",
    "South-west": "SW",
    "South-east": "SE",
    "North-west": "NW",
    "North-east": "NE",
}


def osm_name_to_join_key(row):
    name = row["name"]
    # for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 30, 40]:
    #     prefix = f"{i}00 "
    #     if name.startswith(prefix) and name.split()[1] not in ["Street", "Avenue"]:
    #         name = name[len(prefix) :]
    #         break
    if name.startswith("Mount "):
        name = "mt " + name[len("Mount ") :]
    if name.startswith("Saint "):
        name = "st " + name[len("Saint ") :]
    if name.startswith("St. "):
        name = "st " + name[len("St. ") :]
    if name.startswith("Dr. "):
        name = "dr " + name[len("Dr. ") :]
    if name.startswith("Métis "):
        name = "metis " + name[len("Métis ") :]
    # TODO: remove this
    if name.startswith("Martha's "):
        name = "marthas " + name[len("Martha's ") :]
    for longquad, quad in quads.items():
        if name.endswith(f" {longquad}"):
            name = name[: -len(longquad)] + quad
            break
    return name.lower()


osm["join_key"] = osm.apply(osm_name_to_join_key, axis=1)


joined = coc.merge(osm, on="join_key", how="left", suffixes=("_coc", "_osm"))

# save just the rows in osm_named_streets.geojson that are not in the joined dataframe
osm_not_in_coc = osm[~osm["join_key"].isin(joined["join_key"])]
osm_not_in_coc.to_file("osm_not_in_coc.geojson", driver="GeoJSON")

# do it the other way around and
# save just the rows in Street Centreline_20250225.geojson that are not in the joined dataframe
joined = osm.merge(coc, on="join_key", how="left", suffixes=("_osm", "_coc"))
coc_not_in_osm = coc[~coc["join_key"].isin(joined["join_key"])]
coc_not_in_osm.to_file("coc_not_in_osm.geojson", driver="GeoJSON")
