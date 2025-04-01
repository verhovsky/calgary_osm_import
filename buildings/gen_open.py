from pathlib import Path
import os

with open("open_template.py") as f:
    template = f.read()

Path("./open/").mkdir(exist_ok=True, parents=True)

for file in Path("buildings/neighborhoods").glob("*.geojson"):
    neigh = file.stem
    with open(f"open/{neigh}.command", "w") as f:
        contents = template.replace("{{neigh}}", neigh).replace(
            "{{folder}}", str(Path("buildings").absolute())
        )
        f.write(contents)
    # add exec permission
    os.chmod(f"open/{neigh}.command", 0o755)
