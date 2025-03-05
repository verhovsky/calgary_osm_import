Generaly, school buildings are supposed to be inside a school grounds area with `amenity=school`
and the name of the school should be on the area, not on the school building.

https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dschool

This is for checking that this is the case in Calgary

https://overpass-turbo.eu/s/1ZN3

Run the script like this

```bash
pip install osmnx geopandas
python building_names.py
```

#### Related changesets

- [163235310](https://www.openstreetmap.org/changeset/163235310)
- [163236295](https://www.openstreetmap.org/changeset/163236295)
- [163237488](https://www.openstreetmap.org/changeset/163237488)
- [163237899](https://www.openstreetmap.org/changeset/163237899)
- [163238381](https://www.openstreetmap.org/changeset/163238381)
