from pathlib import Path
import os

with open("open_template.py") as f:
    template = f.read()

Path("./open/").mkdir(exist_ok=True, parents=True)

for file in Path("buildings/neighborhoods").glob("*.geojson"):
    neighborhood = file.stem
    with open(f"open/{neighborhood}.command", "w") as f:
        contents = template.replace("{{neighborhood}}", neighborhood).replace(
            "{{folder}}", str(Path("buildings").absolute())
        )
        f.write(contents)
    # add exec permission
    os.chmod(f"open/{neighborhood}.command", 0o755)
