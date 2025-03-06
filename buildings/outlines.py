import os
from pathlib import Path
import sys
import time
import json
from argparse import ArgumentParser

import geopandas as gpd
from shapely.geometry import Polygon, MultiPolygon
import osmnx as ox

args = ArgumentParser()
args.add_argument("--no-cache", action="store_true")
args = args.parse_args()
cache = not args.no_cache

FILENAME = Path("Buildings.geojson")
OUTPUT_DIR = Path("buildings")

# caching files
SHIFTED_FILENAME = FILENAME.with_name(FILENAME.stem + "_shifted.geojson")
OSM_FILENAME = Path("osm_buildings.geojson")
NEIGHBORHOODS_FILENAME = Path("calgary_neighborhoods.geojson")


def shift_coords(geom, dlat=0.000004, dlon=-0.0000178):
    def shift_polygon(polygon):
        return Polygon([(x + dlon, y + dlat) for x, y in polygon.exterior.coords])

    if geom.geom_type == "Polygon":
        return shift_polygon(geom)
    elif geom.geom_type == "MultiPolygon":
        return MultiPolygon([shift_polygon(poly) for poly in geom.geoms])
    return geom


def expand_osm_tags(row):
    row["building"] = {
        "School Colleges": "school",
        "Commercial": "commercial",
        "Unclassified": "yes",
        "Residential Garage": "garage",
        "Residential Roof Outline": "residential",
    }[row["bldg_code_desc"].strip()]
    return row


def load_shifted():
    # if file exists then just load that
    if SHIFTED_FILENAME.exists() and cache:
        return gpd.read_file(SHIFTED_FILENAME)

    gdf = gpd.read_file(FILENAME, columns=["bldg_code_desc"])
    gdf = gdf[
        gdf["bldg_code_desc"].isin(
            [
                # "Stadium",
                # "Shopping Centres",
                # "LRT Stations and Shelters",
                # "Parking Garages",
                # "Religious",
                "School Colleges",
                # "Miscellaneous (Park Buildings/Structures)",
                # "Building Under Construction",
                # "Bus Shelter",
                "Commercial",
                "Unclassified",
                "Residential Garage",
                "Residential Roof Outline",
            ]
        )
    ]

    # Expand OSM tags into separate columns
    gdf = gdf.apply(expand_osm_tags, axis=1)
    gdf.drop(
        columns=["bldg_code_desc"],
        inplace=True,
    )

    # Remove useless nodes
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=0.000001, preserve_topology=True
    )

    # Adjust coordinates
    gdf["geometry"] = gdf["geometry"].apply(shift_coords)

    gdf["source"] = "City of Calgary Digital Aerial Survey building roof outlines"

    gdf.to_file(SHIFTED_FILENAME, driver="GeoJSON")
    return gdf


def download_buildings(bbox):
    if OSM_FILENAME.exists() and cache:
        return gpd.read_file(OSM_FILENAME)
    gdf = ox.features.features_from_bbox(bbox, {"building": True})
    gdf["geometry"] = gdf["geometry"].simplify(
        tolerance=0.000001, preserve_topology=True
    )
    save_without_nulls(gdf, OSM_FILENAME)
    return gdf


def download_neighborhoods(place: str) -> gpd.GeoDataFrame:
    if NEIGHBORHOODS_FILENAME.exists() and cache:
        return gpd.read_file(NEIGHBORHOODS_FILENAME)

    gdf = ox.features.features_from_place(place, {"boundary": "administrative"})
    gdf = gdf[gdf["admin_level"] == "10"][gdf["boundary"] == "administrative"]
    gdf = gdf.loc[gdf.index.get_level_values("element") == "relation"][
        ["name", "geometry"]
    ]
    gdf.to_file(NEIGHBORHOODS_FILENAME, driver="GeoJSON")
    return gdf


def remove_null_properties(filename):
    with open(filename, "r") as f:
        data = json.load(f)
    for feature in data["features"]:
        feature["properties"] = {
            k: v for k, v in feature["properties"].items() if v is not None
        }
    with open(filename, "w") as f:
        json.dump(data, f)


def save(gdf, filename):
    gdf.to_file(filename, driver="GeoJSON")


def save_without_nulls(gdf, filename):
    gdf.to_file(filename, driver="GeoJSON")
    # https://github.com/geopandas/geopandas/issues/3521
    remove_null_properties(filename)


# Load Calgary buildings data
coc = load_shifted()
print(coc)

# Load OSM data
osm = download_buildings(coc.total_bounds)
print(osm)
# for c in osm.columns:
#     print(c)

# Perform spatial join
osm["osm_id"] = range(1, len(osm) + 1)
coc["coc_id"] = range(1, len(coc) + 1)
result = gpd.sjoin(coc, osm, how="inner")
print(result)

# Find CoC buildings that overlap with an OSM building
osm_only = osm[~osm["osm_id"].isin(result["osm_id"])]
breakpoint()
coc["overlap_count"] = (
    coc["coc_id"].map(result.groupby("coc_id")["osm_id"].nunique()).astype("Int64")
)

print(f"City of Calgary buildings: {len(coc)}")
print(f"OSM buildings: {len(osm)}")
print(f"OSM only: {len(osm_only)}")
# print(coc["overlap_count"].value_counts())

OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
save(
    coc.copy().drop(columns=["coc_id"]),
    OUTPUT_DIR / "coc.geojson",
)
save_without_nulls(
    osm_only.copy().drop(columns=["osm_id"]),
    OUTPUT_DIR / "osm_only.geojson",
)
print("Saved results")

# Split results by neighborhood and print
neighborhoods = download_neighborhoods("Calgary, Alberta, Canada")
coc_by_neighborhoods = gpd.sjoin(coc, neighborhoods, how="inner")


neighborhood_dir = OUTPUT_DIR / "neighborhoods"
neighborhood_dir.mkdir(exist_ok=True, parents=True)
for name, group in coc_by_neighborhoods.groupby("name"):
    safe_name = name.replace("/", "_")
    neighborhood_buildings = coc[coc["coc_id"].isin(group["coc_id"])]
    save(
        neighborhood_buildings.copy().drop(columns=["coc_id"]),
        neighborhood_dir / f"{safe_name}.geojson",
    )
    # print(f"Saved {name}")
no_neighborhood = coc[~coc["coc_id"].isin(coc_by_neighborhoods["coc_id"])]
save(
    no_neighborhood.copy().drop(columns=["coc_id"]),
    OUTPUT_DIR / "coc_outside_calgary.geojson",
)

# Print neighborhood names sorted by number of total of overlap_counts
overlap_counts = {}
for name, group in coc_by_neighborhoods.groupby("name"):
    neighborhood_buildings = coc[coc["coc_id"].isin(group["coc_id"])]
    # convert overlap_count to 0 or 1
    overlap_count = (neighborhood_buildings["overlap_count"] > 0).sum()
    building_count = len(neighborhood_buildings)
    overlap_counts[name] = (overlap_count, building_count)

print()
print("Neighborhoods by number of buildings with OSM overlap:")
for name, count in sorted(overlap_counts.items(), key=lambda x: x[1][0], reverse=True):
    print(f"{name}: {count[0]}/{count[1]}")
