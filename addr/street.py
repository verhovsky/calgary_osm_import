#!/usr/bin/env python3

import osmnx as ox

place = "Calgary, Alberta, Canada"


def fetch_addressed_things_and_streets(place):
    addressed = ox.features.features_from_place(place, {"addr:street": True})
    streets = ox.features.features_from_place(place, {"highway": True})

    return addressed, streets


def find_non_existent_streets(addressed, streets):
    # Remove block numbers from street names
    street_names = [
        "Centre Street NE",
        "Centre Street NW",
        "Centre Street SE",
        "Centre Street SW",
        "Centre Avenue NE",
        "Centre Avenue NW",
        "Centre Avenue SE",
        "Centre Avenue SW",
        "Harvest Hills Boulevard NE",
        "Harvest Hills Boulevard NW",
        "Trans-Canada Highway SW",
        "Trans-Canada Highway NW",
        "Métis Trail NE",
        "Métis Trail NW",
    ]
    for name in sorted(streets["name"].dropna().unique()):
        for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 20, 30, 40]:
            prefix = f"{i}00 "
            # We keep "100 Avenue" or "100 Street" as that might be the actual name
            if name.startswith(prefix) and not (
                name.startswith(prefix + "Avenue") or name.startswith(prefix + "Street")
            ):
                name = name[len(prefix) :]
                break
        street_names.append(name)

    street_names_set = set(street_names)

    # Filter addressed things with address street names that do not match existing street names
    unmatched_streets = addressed[
        addressed["addr:street"].apply(lambda x: x not in street_names_set)
    ]

    return unmatched_streets


addressed, streets = fetch_addressed_things_and_streets(place)
unmatched_addresses = find_non_existent_streets(addressed, streets)

print(unmatched_addresses)
unmatched_addresses.to_file("unmatched_addr-street.geojson", driver="GeoJSON")
