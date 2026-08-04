from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {
    ROOT
    / "static"
    / "js"
    / "htmx.min.js": "https://cdn.jsdelivr.net/npm/htmx.org@2.0.10/dist/htmx.min.js",
}

for target, url in ASSETS.items():
    target.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(url, timeout=30) as response:
        target.write_bytes(response.read())
    print(f"Downloaded {target.relative_to(ROOT)}")
