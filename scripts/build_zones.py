"""Build custom_components/esolatgps/data/jakim_zones.json.gz (dev tool, not shipped logic).

Sources:
  * District polygons tagged with JAKIM zone codes: mptwaktusolat/jakim.geojson
    (malaysia.district-jakim.geojson, itself derived from nullifye/malaysia.geojson).
  * Zone names (negeri/daerah): https://api.waktusolat.app/zones

Polygons are simplified (~110 m tolerance) and rounded to 4 decimals (~11 m) to keep the
file small. Requires: pip install shapely
Usage: python scripts/build_zones.py
"""
import gzip
import json
import urllib.request
from datetime import date
from pathlib import Path

from shapely.geometry import shape

GEOJSON_URL = (
    "https://raw.githubusercontent.com/mptwaktusolat/jakim.geojson/"
    "master/malaysia.district-jakim.geojson"
)
ZONES_URL = "https://api.waktusolat.app/zones"
TOLERANCE = 0.001
OUT = Path(__file__).resolve().parents[1] / "custom_components/esolatgps/data/jakim_zones.json.gz"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "esolatgps-build"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


SCALE = 10_000  # 4 decimals, ~11 m


def ring(coords):
    """Flat ring as integer deltas: first point absolute (x1e4), then the step to each next point."""
    out, px, py = [], 0, 0
    for xy in coords:
        x, y = round(xy[0] * SCALE), round(xy[1] * SCALE)
        out += [x - px, y - py]
        px, py = x, y
    return out


def main():
    gj = fetch(GEOJSON_URL)
    names = {z["jakimCode"]: {"negeri": z.get("negeri"), "daerah": z.get("daerah")} for z in fetch(ZONES_URL)}
    districts = []
    for f in gj["features"]:
        p = f["properties"]
        if not p.get("jakim_code"):
            continue
        g = shape(f["geometry"]).buffer(0).simplify(TOLERANCE, preserve_topology=True)
        polys = []
        for poly in getattr(g, "geoms", [g]):
            if poly.is_empty:
                continue
            polys.append([ring(poly.exterior.coords), *[ring(i.coords) for i in poly.interiors]])
        minx, miny, maxx, maxy = g.bounds
        districts.append({
            "z": p["jakim_code"], "d": p["name"], "s": p["state"],
            "b": [round(minx, 4), round(miny, 4), round(maxx, 4), round(maxy, 4)],
            "p": polys,
        })
    out = {
        "version": date.today().isoformat(),
        "format": 2,  # rings are integer deltas at 1e-4 degrees
        "scale": SCALE,
        "source": "mptwaktusolat/jakim.geojson + api.waktusolat.app/zones",
        "zones": names,
        "districts": districts,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(out, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    OUT.write_bytes(gzip.compress(raw, 9, mtime=0))  # mtime=0 keeps rebuilds byte-identical
    print(f"{len(districts)} districts, {len(names)} zones, {OUT.stat().st_size // 1024} KB -> {OUT}")


if __name__ == "__main__":
    main()
