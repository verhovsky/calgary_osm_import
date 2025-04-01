# [Building outlines](https://data.calgary.ca/Base-Maps/Building-Roof-Outlines/sh7p-758r)

Download the data as GeoJSON from

https://data.calgary.ca/Base-Maps/Buildings/uc4c-6kbd/about_data

and save it as Buildings.geojson (remove the download date)

As of Feb 1 2025 the stats for building type were

```text
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

Download parcel address data (as a CSV, if you try GeoJSON it downloads an empty file) from

https://data.calgary.ca/Base-Maps/Parcel-Address/9zvu-p8uz/about_data

and save it as "Parcel Address.csv" (remove download date)

Run the Python code like this:

```sh
pip install geopandas shapely osmnx
python osmify_addresses.py
python outlines.py
```

osmify_addresses.py converts an address like this

```py
{
    "STREET_NAME": "CENTRE",
    "STREET_TYPE": "ST",
    "STREET_QUAD": "SW",
    "HOUSE_NUMBER": "1",
    "HOUSE_ALPHA": "A"
}
```

into

```py
{
    "addr:unit": "A",
    "addr:housenumber": "1",
    "addr:street": "Centre Street SW"
}
```

where the generated `addr:street` column is always a street name already in Open Street Map (somewhere in Calgary, there's no check that it's actually near the address point).

osmify_addresses.py outputs two files:

- Parcel_Address_osm.geojson with the converted data
- Parcel_Address_not_in_osm.geojson address points where the generated `addr:street` value doesn't have a matching street in Open Street Map


outlines.py will use Parcel_Address_osm.geojson and Buildings.geojson and create a directory buildings/ with:

- neighborhoods/ a directory with outlines split into neighborhoods (buildings that straddle a neighborhood boundary and might be duplicated accross neighborhoods)
- addresses/ address points split into neighborhoods
- outside_calgary.geojson outlines outside the legal city bounds

and a neighborhoods/ directory, with City of Calgary buildings grouped by the neighborhood they're in. Each geometry will also have an `overlap_count` column if
it overlaps with any existing building(s) in OpenStreetMap. To import the data, open one of the neighborhoods in JOSM and

1. Click "Validation", there will probably be a couple overlapping buildings, separate them. Buildings with holes (courtyards) need to be converted to relations
2. Check that every building is classified correctly using the "Building Colors" map paint style
3. (optionally) Convert `building=residential` to a more specific residence type
4. (optionally) Open the addresses dataset for the neighborhood and use the [Conflation JOSM plugin](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/Conflation) to merge it with the `building=residential` outlines
5. Download OSM data for the current region, search for `building:` in OSM data and `type:way` in CoC data and use the [Conflation JOSM plugin](https://wiki.openstreetmap.org/wiki/JOSM/Plugins/Conflation) and decide how to merge overlapping buildings
6. Click "Validation" and fix all "Crossing \<whatever\>/building" and "Overlap \<whatever\>/building" warnings
7. Upload the data

Verify there's no accidentally uploaded `overlap_count` keys in OSM at https://overpass-turbo.eu/s/1ZRW

### Data issues

##### outlines

- slightly offset from Bing imagery
- contain a lot of unnecessary nodes and `.simplify()` doesn't get rid of all of them
- can overlap slightly
- barely touching outlines sometimes share a random node with another outline and have overlap errors because of that
- are generally really good, but shadows sometimes mess it up
- building types are sometimes misclassified
- outlines with holes (courtyards) need to be turned into `multipolygon` relations manually
- sometimes there's an outline where there's just trees in Bing, so it's impossible to verify that there's something there

##### addresses

Addresses are for land parcels, not buildings, so they

- do not line up with the house outline, generally closer to the street than the house
- duplexes will have two address points for the same building outline
- appartment buildings/townhouses (and maybe some regular houses) usually have wrong "house" numbers that don't correspond to the actual house number, would require surveying to verify
