# school buildings shouldn't have names, the name should be on the school area
# there are a few exceptions where the area and the school are different
# https://overpass-turbo.eu/s/1ZN3

# this script gets all school buildings with names, then all school areas
# and matches them up, if the area and building have the same name, it needs
# to be deleted so it generates a overpass query to get all those buildings
# if the area has no name, it generates a query to get all buildings on that area
# to make it easy to move the names from the buildings to the areas
# if the names are different, it prints them

import geopandas as gpd
import osmnx as ox

bbox = [-114.3387482, 50.8341488, -113.8194342, 51.2270627]

buildings = ox.features.features_from_bbox(bbox, {"building": "school"})
areas = ox.features.features_from_bbox(bbox, {"amenity": "school"})


buildings = buildings[buildings["name"].notnull()]

overlap = gpd.sjoin(buildings, areas, how="inner")
named_buildings = overlap[overlap["name_left"] == overlap["name_right"]]

duplicated_names = buildings[buildings.index.isin(named_buildings.index)]

print(f"Overpass query for {len(duplicated_names)} duplicated names:")
print(f"""[out:json];
(
    {"\n    ".join(f"{index[0]}({index[1]});" for index, _ in duplicated_names.iterrows())}
);
out body;
>;
out skel qt;""")
print()

empty_named_area_buildings = overlap[overlap["name_right"].isnull()]
empty_named_areas = areas[areas["name"].isnull()]
print(
    f"Overpass query for {len(empty_named_area_buildings)} empty named areas and schools on them:"
)
print(f"""[out:json];
(
    // schools
    {"\n    ".join(f"{index[0]}({index[1]});" for index, _ in empty_named_area_buildings.iterrows())}
    // empty named areas
    {"\n    ".join(f"{index[0]}({index[1]});" for index, _ in empty_named_areas.iterrows())}
);
out body;
>;
out skel qt;""")
print()

# print the names that are different
for index, row in overlap[overlap["name_left"] != overlap["name_right"]].iterrows():
    print(row["name_left"])
    print("  " + row["name_right"])
