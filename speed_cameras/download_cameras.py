import sys
import re
import json

import requests
from geopy.distance import geodesic


# https://data.calgary.ca/Health-and-Safety/Intersection-Safety-Cameras/dv2f-necx/about_data
# You have to manually exit the descriptions for the cameras to get the direction
FILENAME = "Intersection Safety Cameras_20250221.geojson"


def load_geojson(file_path):
    """Load a GeoJSON file and return the feature collection."""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data["features"]


def download_osm_cameras():
    url = "http://overpass-api.de/api/interpreter"

    # Get all speed cameras in Calgary administrative boundary
    query = """
    [out:json][timeout:50];
    // Fetch Calgary's administrative boundary
    area["name"="Calgary"]["admin_level"="6"]->.calgary;
    // Gather results for speed cameras within Calgary
    (
      node["highway"="speed_camera"](area.calgary);
      way["highway"="speed_camera"](area.calgary);
      relation["highway"="speed_camera"](area.calgary);
    );
    // Print results
    out body;
    >;
    out skel qt;
    """

    response = requests.get(url, params={"data": query})

    if response.status_code == 200:
        data = response.json()
        elements = data["elements"]

        # Check for missing direction tag
        missing = False
        for osm_camera in elements:
            if "direction" not in osm_camera["tags"]:
                print(f"OSM camera missing direction: {osm_camera}", file=sys.stderr)
                missing = True
        if missing:
            sys.exit(1)

        # Check for overlapping/duplicate cameras
        for i, osm_camera in enumerate(elements):
            for other_camera in elements[i + 1 :]:
                if osm_camera == other_camera:
                    continue
                osm_coord = (osm_camera["lat"], osm_camera["lon"])
                other_coord = (other_camera["lat"], other_camera["lon"])
                if geodesic(osm_coord, other_coord).meters < 100 and (
                    osm_camera["tags"]["direction"] == other_camera["tags"]["direction"]
                ):
                    print(
                        f"OSM cameras overlap: {osm_camera} and {other_camera}",
                        file=sys.stderr,
                    )
                    sys.exit(1)

        return elements
    else:
        print("Failed to fetch data: ", response.status_code, response.text)
        sys.exit(1)


def parse_description(features):
    for feature in features:
        description = feature["properties"]["description"]
        try:
            direction = re.search(r"\bDirection\s*:\s*(.+)", description).group(1)
            if direction not in ["Northbound", "Southbound", "Eastbound", "Westbound"]:
                print(
                    "Invalid direction, you have to manually fix the file:", direction
                )
                sys.exit(1)
            feature["properties"]["direction"] = {
                "northbound": 0,
                "eastbound": 90,
                "southbound": 180,
                "westbound": 270,
            }[direction.lower()]
        except Exception:
            print(
                "Invalid description, you have to manually edit the file to match this format: 'Direction: [Northbound,Eastbound,Southbound,Westbound]':",
                repr(description),
            )
            sys.exit(1)
    return features


def quantize_direction(direction):
    direction = int(direction) % 360
    if direction < 45:
        return 0
    if direction < 135:
        return 90
    if direction < 225:
        return 180
    if direction < 315:
        return 270
    return 0


coc_cameras = parse_description(load_geojson(FILENAME))
osm_cameras = download_osm_cameras()

existing_features = []
new_features = []

for feature in coc_cameras:
    coords = feature["geometry"]["coordinates"]
    coords = (coords[1], coords[0])  # my favorite part of working with geo data
    direction = feature["properties"]["direction"]
    exists = False
    for osm_camera in osm_cameras:
        osm_coord = (osm_camera["lat"], osm_camera["lon"])
        osm_direction = osm_camera["tags"]["direction"]
        if (
            geodesic(osm_coord, coords).meters < 100
            and quantize_direction(osm_direction) == direction
        ):
            print(f"{coords} already exist in OSM at {osm_coord}", file=sys.stderr)
            exists = True
            break
    if not exists:
        new_features.append(feature)
    else:
        existing_features.append(feature)


def to_osm(features):
    processed = []

    for feature in features:
        feature = feature.copy()
        feature["properties"]["highway"] = "speed_camera"
        processed.append(feature)
    return processed


existing_fc = {
    "type": "FeatureCollection",
    "features": to_osm(existing_features),
}

new_fc = {"type": "FeatureCollection", "features": to_osm(new_features)}

with open("existing_cameras.geojson", "w") as f:
    json.dump(existing_fc, f, indent=2)

with open("new_cameras.geojson", "w") as f:
    json.dump(new_fc, f, indent=2)


print(f"Existing cameras: {len(existing_features)}")
print(f"New cameras: {len(new_features)}")
