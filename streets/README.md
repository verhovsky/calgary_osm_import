Download the data as GeoJSON from here

https://data.calgary.ca/Transportation-Transit/Street-Centreline/4dx8-rtm5/about_data

Then save the result of this query as streets.geojson

https://overpass-turbo.eu/s/1Zn5

Then run the Python script like this

```sh
pip install geopandas
python names.py
```

it will create two files

- osm_not_in_coc.geojson streets in OpenStreetMap that don't have a street with the same name in City of Calgary data
- coc_not_in_osm.geojson streets in the City of Calgary data that don't have a street with the same name in OpenStreetMap

Useful reasons for discrepancies are

- newly constructed streets
- incorrectly named streets
- missing block numbers like "400 Abalone Place NE" vs just "Abalone Place Ne"
- typos in OpenStreetMap

Useless reasons are:

- unnecessary block numbers like "100 West Springs Place SW" when there's no 200 and the street sign doesn't have it either
- streets with names that descriptions not names like "Queen's Park Cemetery 10 Street entrance"
- streets in private condo complexes are usually unnamed but could be named after the complex
- apostrophes
- abbreviations like St. and Mt.
- mistakes in the Calgary data/street signs like "Abbot" vs. "Abbott" or missing spaces
