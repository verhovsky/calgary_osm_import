Download the City of Calgary data as GeoJSON here

https://data.calgary.ca/Health-and-Safety/Intersection-Safety-Cameras/dv2f-necx/about_data

Then open it in a text editor and edit it by hand to actually say "Direction: <direction>" in a consistent way. Some cameras just say "NB" instead of "Direction: Northbound", etc.

Then run the script like this

```sh
pip install requests geopy
python download_cameras.py
```

You may need to update the `FILENAME =` line to match the file you downloaded above

It will create 2 files:

- existing_cameras.geojson City of Calgary cameras that already have a matching camera in OpenStreetMap
- new_cameras.geojson City of Calgary cameras that could not be matched to a speed_camera in OpenStreetMap
