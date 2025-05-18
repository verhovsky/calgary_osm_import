#!/usr/bin/env python3

import subprocess
import urllib

import geopandas as gpd
import osmnx as ox
import pandas as pd

BBOX = [-114.3387482, 50.8341488, -113.8194342, 51.2270627]

# ------------------------------------------------------------
# Input data
# ------------------------------------------------------------
print("[INFO] Reading community boundaries from CSV...")
# https://data.calgary.ca/Base-Maps/Community-Boundaries/ab7m-fwn6
communities = gpd.read_file("Community_District_Boundaries.csv")

NAME_REPLACEMENTS = {
    "KILLARNEY/GLENGARRY": "KILLARNEY",
    "NORTH HAVEN UPPER": "UPPER NORTH HAVEN",
    "DOUGLASDALE/GLEN": "DOUGLASDALE/DOUGLAS GLEN",
    # City of Calgary should fix this
    "QUEENS PARK VILLAGE": "QUEEN'S PARK VILLAGE",
    # These might be wrong in OSM
    "GREENVIEW INDUSTRIAL PARK": "GREENVIEW INDUSTRIAL",
    "NORTH GLENMORE PARK": "NORTH GLENMORE",
}
communities["NAME"] = communities["NAME"].replace(NAME_REPLACEMENTS)

# ------------------------------------------------------------
# OSM "neighborhood" relations (admin_level=10)
# ------------------------------------------------------------
print("[INFO] Downloading OSM neighborhood boundaries...")
neighborhoods = ox.features.features_from_place(
    "Calgary, Alberta, Canada",
    tags={"boundary": "administrative", "admin_level": "10"},
)

neighborhoods = neighborhoods[neighborhoods["admin_level"] == "10"]
# and only boundary=administrative
neighborhoods = neighborhoods[neighborhoods["boundary"] == "administrative"]
# and only relations
neighborhoods = neighborhoods.loc[
    neighborhoods.index.get_level_values("element") == "relation"
]
print(f"[INFO] Retrieved {len(neighborhoods)} OSM neighborhoods.")

# Move relation id into a column
neighborhoods["neighborhood_id"] = neighborhoods.index.get_level_values("id")
# Normalise name for joining
neighborhoods["NAME"] = neighborhoods["name"].str.upper()

# ------------------------------------------------------------
# Add neighborhood type (Residential / Industrial / …)
# ------------------------------------------------------------
print("[INFO] Joining city 'CLASS' info to OSM neighborhoods...")
neighborhoods = neighborhoods.merge(
    communities[["NAME", "CLASS", "SRG"]],
    on="NAME",
    how="left",
    suffixes=("", "_calgary"),
)
neighborhoods = neighborhoods.rename(
    columns={"CLASS": "neighborhood_type", "SRG": "neighborhood_status"}
)

matched = neighborhoods["neighborhood_type"].notnull().sum()
print(f"[INFO] Matched {matched} neighborhoods with city data.")
if matched < len(neighborhoods):
    unmatched = neighborhoods.loc[neighborhoods["neighborhood_type"].isnull(), "name"]
    print(
        f"[WARN] {len(unmatched)} neighborhoods were not matched:\n", unmatched.tolist()
    )

# ------------------------------------------------------------
# Download all buildings inside Calgary bounding box
# ------------------------------------------------------------
print("[INFO] Downloading OSM buildings...")
buildings = ox.features.features_from_bbox(BBOX, {"building": True})
print(f"[INFO] Retrieved {len(buildings)} buildings.")

# Ensure required columns exist
for col in ("source", "addr:street", "building", "note"):
    if col not in buildings.columns:
        buildings[col] = None

# ------------------------------------------------------------
# Spatial join: assign each building to a neighborhood
# ------------------------------------------------------------
print("[INFO] Performing spatial join...")
# target_crs = "EPSG:3857"
# neighborhoods = neighborhoods.to_crs(target_crs)
# buildings = buildings.to_crs(target_crs)

joined = gpd.sjoin(
    buildings,
    neighborhoods[
        [
            "geometry",
            "name",
            "neighborhood_id",
            "neighborhood_type",
            "neighborhood_status",
        ]
    ].rename(columns={"name": "_neighborhood"}),
    how="left",
)
print(joined["_neighborhood"].notnull().sum())

assigned = joined["_neighborhood"].notnull().sum()
print(f"[INFO] Assigned {assigned} buildings to a neighborhood.")
print(f"[INFO] Unassigned buildings: {len(joined) - assigned}")

# ------------------------------------------------------------
# OSM addr points
# ------------------------------------------------------------
print("[INFO] Downloading OSM address points...")
addr_points = ox.features.features_from_bbox(
    BBOX, {"addr:street": True, "addr:housenumber": True}
)
print(f"[INFO] Retrieved {len(addr_points)} address points.")
# Ensure required columns exist
for col in ("addr:street", "addr:housenumber"):
    if col not in addr_points.columns:
        addr_points[col] = None
# Spatial join: assign each address point to a neighborhood
# and map neighborhood name to number of addr points in it
addr_points = gpd.sjoin(
    addr_points,
    neighborhoods[["geometry", "name"]].rename(columns={"name": "_neighborhood"}),
    how="left",
)
# Count number of address points in each neighborhood
# and turn into a dict
addr_points = addr_points.groupby("_neighborhood").size().to_dict()

# ------------------------------------------------------------
# Per-neighborhood summary
# ------------------------------------------------------------
print("[INFO] Generating per-neighborhood stats...")
RESIDENTIAL_CODES = {"residential", "house", "detached", "yes"}


def stats(group):
    name = group["_neighborhood"].iloc[0]
    neighborhood_id = int(group["neighborhood_id"].iloc[0])
    neighborhood_type = group["neighborhood_type"].iloc[0]
    neighborhood_status = group["neighborhood_status"].iloc[0]

    total = len(group)
    residential = len(group[group["building"].isin(RESIDENTIAL_CODES)])
    coc = len(
        group[
            group["source"]
            == "City of Calgary Digital Aerial Survey building roof outlines"
        ]
    ) + len(
        group[
            group["note"]
            == "City of Calgary rooflines - aquisition date - 2024-06-12T22:39:34.000Z"
        ]
    )
    coc_ration = coc / total if total else 0
    addr = int(group["addr:street"].notnull().sum())
    if name in addr_points:
        addr += addr_points[name]
    addr_ratio = addr / residential if residential else 0
    return pd.Series(
        {
            "total": total,
            "residential": residential,
            "coc_sourced": coc,
            "coc_ratio": coc_ration,
            "addressed": addr,
            "addr_ratio": addr_ratio,
            "neighborhood_type": neighborhood_type,
            "status": neighborhood_status,
            "id": neighborhood_id,
            "link": f"https://openstreetmap.org/relation/{neighborhood_id}",
        }
    )


summary = joined.dropna(subset=["_neighborhood"]).groupby("_neighborhood").apply(stats)
# only Residential and with more than 100 buildings
summary = summary[summary["total"] > 100]
# summary = summary.sort_index()

# Print summary (can be saved as CSV too)
print("\n[STATS] Per-Neighborhood Building Summary")
print(
    summary.sort_values("addr_ratio", ascending=False)
    .reset_index()
    .to_string(index=False)
)
print()
print(
    summary.sort_values("coc_ratio", ascending=False)
    .reset_index()
    .to_string(index=False)
)


def open_neigh(summary, comment=""):
    query = f"""// {len(summary)} {comment}
"""
    ids = summary["id"].tolist()
    if ids:
        query += "relation(id: " + ",".join(map(str, ids)) + ");"
    query += """
out geom;"""
    url = "https://overpass-turbo.eu/?c=Aa9rwgieiL&R=&Q=" + urllib.parse.quote(query)
    # print(url)
    subprocess.run(["open", url])


summary = summary[
    (summary["neighborhood_type"] == "Residential")
    & (summary["total"] > 100)
    & summary["status"].isin(["COMPLETE", "ESTABLISHED"])
]
open_neigh(
    summary[summary["addr_ratio"] < 0.9],
    "Calgary neighborhoods where less than 90% of residential buildings have an address",
)
open_neigh(
    summary[summary["coc_ratio"] < 0.55],
    "Calgary neighborhoods where less than 55% of buildings are sourced from the City of Calgary",
)
# both
open_neigh(
    summary[(summary["coc_ratio"] < 0.55) & (summary["addr_ratio"] < 0.9)],
    "Calgary neighborhoods where less than 55% of buildings are sourced from the City of Calgary and less than 90% of residential buildings have an address",
)

# ------------------------------------------------------------
# Step 2: Streets and Sidewalks by Neighborhood
# ------------------------------------------------------------
print("[INFO] Downloading Calgary highways...")
highway_tags = {
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
    ]
}
streets = ox.features.features_from_bbox(BBOX, highway_tags)

# Filter LineStrings only and convert CRS for accurate length calc
streets = streets[streets.geometry.type.isin(["LineString", "MultiLineString"])]
streets = streets.set_geometry("geometry").to_crs("EPSG:4326")
streets["length_m"] = streets.geometry.length

# Assign neighborhoods
streets_joined = gpd.sjoin(
    streets,
    neighborhoods[["geometry", "name"]].rename(columns={"name": "_neighborhood"}),
    how="left",
)
streets_by_neigh = streets_joined.groupby("_neighborhood")["length_m"].sum()

print("[INFO] Downloading sidewalks...")
sidewalks = ox.features.features_from_bbox(BBOX, {"highway": "footway"})
sidewalks = sidewalks[sidewalks.geometry.type.isin(["LineString", "MultiLineString"])]
sidewalks = sidewalks.set_geometry("geometry").to_crs("EPSG:4326")
sidewalks["length_m"] = sidewalks.geometry.length

sidewalks_joined = gpd.sjoin(
    sidewalks,
    neighborhoods[["geometry", "name"]].rename(columns={"name": "_neighborhood"}),
    how="left",
)
sidewalks_by_neigh = sidewalks_joined.groupby("_neighborhood")["length_m"].sum()

# ------------------------------------------------------------
# Combine into sidewalk-to-street ratio
# ------------------------------------------------------------
print("[INFO] Calculating sidewalk-to-street ratios...")
length_df = pd.DataFrame(
    {
        "street_length_m": streets_by_neigh,
        "sidewalk_length_m": sidewalks_by_neigh,
    }
)
length_df["sidewalk_ratio"] = (
    length_df["sidewalk_length_m"] / length_df["street_length_m"]
)

# Merge into summary
new_summary = summary.merge(length_df, left_index=True, right_index=True, how="left")

print("\n[STATS] Sidewalk Coverage Summary")
print(
    new_summary[new_summary["sidewalk_ratio"].notnull()]
    .sort_values("sidewalk_ratio")
    .reset_index()[
        [
            "_neighborhood",
            "id",
            "sidewalk_ratio",
            "street_length_m",
            "sidewalk_length_m",
        ]
    ]
    .to_string(index=False)
)

open_neigh(
    new_summary[
        (new_summary["sidewalk_ratio"] < 0.657)
        & (new_summary["neighborhood_type"] == "Residential")
    ],
    "Calgary neighborhoods where total sidewalk length is less than total street length",
)


a = new_summary[
    (new_summary["sidewalk_ratio"] < 0.657)
    & (new_summary["neighborhood_type"] == "Residential")
]
print("{{columns|width=18|")
for index, row in a.sort_values("sidewalk_ratio").iterrows():
    relation_id = int(row["id"])
    name = index  # because _neighborhood is the index
    print(f"* {{{{Relation|{relation_id}|{name}}}}}")
print("}}")
