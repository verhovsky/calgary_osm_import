#!/usr/bin/env python
import os
import subprocess
from pathlib import Path

import geopandas as gpd
import requests

neighborhood = "{{neighborhood}}"

folder = Path("{{folder}}")


def enable_bing_imagery():
    josm_url = "http://127.0.0.1:8111/imagery"
    params = {
        "id": "Bing",
    }
    response = requests.get(josm_url, params=params)
    print(f"Enabling Bing imagery: {response.status_code} - {response.reason}")


def open_file_in_josm(file_path):
    josm_url = "http://127.0.0.1:8111/open_file"
    full_path = os.path.abspath(file_path)
    response = requests.get(f"{josm_url}?filename={full_path}")
    print(f"Opening {file_path}: {response.status_code} - {response.reason}")


def get_and_adjust_bbox(file_path, delta_lat, delta_lon):
    # Load GeoJSON file
    gdf = gpd.read_file(file_path)

    # Calculate bounding box
    bbox = gdf.total_bounds  # Returns [minx, miny, maxx, maxy]

    # Adjust bounding box
    adjusted_bbox = [
        bbox[0] - delta_lon,
        bbox[1] - delta_lat,
        bbox[2] + delta_lon,
        bbox[3] + delta_lat,
    ]
    return adjusted_bbox


def download_osm_data_for_bbox(bbox):
    josm_url = "http://127.0.0.1:8111/load_and_zoom"
    params = {
        "left": bbox[0],
        "bottom": bbox[1],
        "right": bbox[2],
        "top": bbox[3],
        "new_layer": "true",
        "layer_name": "osm",
        "search": "-type:relation building:",
    }
    response = requests.get(josm_url, params=params)
    print(
        f"Downloading OSM data for bbox {bbox}: {response.status_code} - {response.reason}"
    )


subprocess.run(["open", "/Applications/JOSM.app"])

enable_bing_imagery()

# Path to the GeoJSON files
file1 = folder / "addresses" / f"{neighborhood}.geojson"
file2 = folder / "neighborhoods" / f"{neighborhood}.geojson"

# Open GeoJSON files in JOSM
open_file_in_josm(file1)
open_file_in_josm(file2)

# Get and adjust the bounding box of the second file
bbox1 = get_and_adjust_bbox(file1, 0.0001, 0.00005)
bbox2 = get_and_adjust_bbox(file2, 0.0001, 0.00005)
bbox = [
    min(bbox1[0], bbox2[0]),
    min(bbox1[1], bbox2[1]),
    max(bbox1[2], bbox2[2]),
    max(bbox1[3], bbox2[3]),
]
download_osm_data_for_bbox(bbox)
