# [Building outlines](https://data.calgary.ca/Base-Maps/Building-Roof-Outlines/sh7p-758r)

Download the data as GeoJSON from

https://data.calgary.ca/Base-Maps/Buildings/uc4c-6kbd/about_data

and save it as Buildings.geojson (remove the download date)

As of Feb 1 2025 the stats for building type were

```
Residential Roof Outline                     343282
Residential Garage                           119825
Unclassified                                  11880
Commercial                                    11300
Bus Shelter                                    1864
Building Under Construction                    1449
Miscellaneous (Park Buildings/Structures)       673
School Colleges                                 588
Religious                                       289
Parking Garages                                 216
LRT Stations and Shelters                       127
Shopping Centres                                 92
Stadium                                          13
```

Some of the categories like `Bus Shelter` are handled separately.

Run the Python code like this:

```sh
pip install geopandas shapely osmnx
python outlines.py
```

it will create a directory buildings/ with 3 files:

- osm_only.geojson buildings in OSM that don't overlap with City of Calgary buildings (this is not entirely true, because some building types are ignored)
- coc.geojson all City of Calgary buildings
- coc_outside_calgary.geojson City of Calgary buildings that are technically outside the city boundary and don't belong to any neighborhood

and a neighborhoods/ directory, with City of Calgary buildings grouped by the neighborhood they're in. Each geometry will also have an `overlap_count` column if
it overlaps with any existing building(s) in OpenStreetMap. To import the data, open one of the neighborhoods in JOSM and

1. Click "Validation", there will probably be a couple overlapping buildings, separate them. Buildings with holes (courtyards) need to be converted to relations
2. Check that every building is classified correctly using the "Building Colors" map paint style
3. Optionally convert `building=residential` to a more specific residence type
4. Download OSM data for the current region and merge the OSM layer and neighborhood CoC outlines layer
5. Search for `type:way overlap_count:` and decide what to do with each overlapping outline. Usually you want to select both overlapping outlines and do "Replace Geometry" (or Ctrl-Shift-G) to replace the OSM building's geometry with the CoC geometry or delete the CoC outline if the existing OSM outline is good. Do this until there's no overlapping buildings
6. Click "Validation" and fix all "Crossing \<whatever\>/building" and "Overlap \<whatever\>/building" warnings
7. Search for `overlap_count:` and delete all the `overlap_count` keys, they should not be uploaded to OpenStreetMap
8. Upload the data

Verify there's no accidentally uploaded `overlap_count` keys in OSM at https://overpass-turbo.eu/s/1ZRW
