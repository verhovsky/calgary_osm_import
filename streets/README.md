Download the data as GeoJSON from here

https://data.calgary.ca/Transportation-Transit/Street-Centreline/4dx8-rtm5/about_data

and save it as Street Centreline.geojson (remove the download date from the filename)

Then run the Python script like this

```sh
pip install geopandas
python names.py
```

it will print missing street names in each dataset and their closest match and then create three files

- osm_not_in_coc.geojson Calgary streets in OpenStreetMap that don't have a street with the same name in City of Calgary data
- coc_not_in_osm.geojson streets in City of Calgary open data that don't have a street with the same name in OpenStreetMap
- osm_streets.geojson all named streets in Calgary in OpenStreetMap

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
