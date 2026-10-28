"""Offline GPS -> JAKIM zone lookup from the bundled district polygons.

data/jakim_zones.json.gz is built by scripts/build_zones.py from mptwaktusolat/jakim.geojson.
Lookup is a bounding-box prefilter plus ray casting; no network and well under a millisecond.
"""
from __future__ import annotations

import gzip
import json
import math
from dataclasses import dataclass
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "jakim_zones.json.gz"

# A point within this distance of a district (but not inside it) still counts as that district.
# Covers coastlines lost to simplification, jetties, ferries and GPS drift at the shore.
NEAR_KM = 3.0
_KM_PER_DEG = 111.32


@dataclass(frozen=True)
class ZoneMatch:
    """Result of a lookup."""

    zone: str          # JAKIM code, e.g. "SGR01"
    district: str      # polygon's district, e.g. "Hulu Langat"
    state: str         # short state code from the polygon, e.g. "SGR"
    negeri: str | None  # JAKIM state name, e.g. "Selangor"
    daerah: str | None  # JAKIM zone description, e.g. "Gombak, Petaling, Sepang, ..."
    exact: bool        # False when matched by the NEAR_KM coastal tolerance


class ZoneIndex:
    """In-memory polygon index. Build once (blocking file read) and reuse."""

    def __init__(self, data: dict) -> None:
        self.version: str = data.get("version", "")
        self.zones: dict[str, dict] = data.get("zones", {})
        districts = data["districts"]
        if data.get("format") == 2:
            scale = data.get("scale", 10_000)
            districts = [{**d, "p": [[_decode(r, scale) for r in rings] for rings in d["p"]]} for d in districts]
        self._districts = districts

    @classmethod
    def load(cls, path: Path = DATA_FILE) -> "ZoneIndex":
        """Blocking: run in an executor."""
        raw = path.read_bytes()
        if raw[:2] == b"\x1f\x8b":
            raw = gzip.decompress(raw)
        return cls(json.loads(raw))

    def lookup(self, latitude: float, longitude: float) -> ZoneMatch | None:
        """Zone for a coordinate, or None when it is not in (or next to) Malaysia."""
        try:
            lat, lon = float(latitude), float(longitude)
        except (TypeError, ValueError):
            return None

        for d in self._districts:
            minx, miny, maxx, maxy = d["b"]
            if minx <= lon <= maxx and miny <= lat <= maxy and _in_district(d["p"], lon, lat):
                return self._match(d, True)

        # Not inside any polygon: accept the nearest district within NEAR_KM
        pad = NEAR_KM / _KM_PER_DEG
        kx = math.cos(math.radians(lat))
        best, best_km = None, NEAR_KM
        for d in self._districts:
            minx, miny, maxx, maxy = d["b"]
            if not (minx - pad / max(kx, 0.1) <= lon <= maxx + pad / max(kx, 0.1) and miny - pad <= lat <= maxy + pad):
                continue
            km = _distance_km(d["p"], lon, lat, kx)
            if km <= best_km:
                best, best_km = d, km
        return self._match(best, False) if best else None

    def zone_info(self, zone: str) -> dict:
        return self.zones.get(zone, {})

    def _match(self, d: dict, exact: bool) -> ZoneMatch:
        info = self.zones.get(d["z"], {})
        return ZoneMatch(d["z"], d["d"], d["s"], info.get("negeri"), info.get("daerah"), exact)


def _decode(ring: list[int], scale: int) -> list[float]:
    """Integer deltas back to flat absolute float coordinates."""
    out: list[float] = []
    x = y = 0
    for i in range(0, len(ring), 2):
        x += ring[i]
        y += ring[i + 1]
        out += [x / scale, y / scale]
    return out


def _in_ring(ring: list[float], x: float, y: float) -> bool:
    inside = False
    n = len(ring) // 2
    j = n - 1
    for i in range(n):
        xi, yi = ring[2 * i], ring[2 * i + 1]
        xj, yj = ring[2 * j], ring[2 * j + 1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _in_district(polys: list, x: float, y: float) -> bool:
    for rings in polys:
        if _in_ring(rings[0], x, y) and not any(_in_ring(h, x, y) for h in rings[1:]):
            return True
    return False


def _distance_km(polys: list, x: float, y: float, kx: float) -> float:
    """Shortest distance from the point to any polygon edge (equirectangular, fine at a few km)."""
    best = math.inf
    for rings in polys:
        for ring in rings:
            n = len(ring) // 2
            for i in range(n - 1):
                ax, ay = (ring[2 * i] - x) * kx, ring[2 * i + 1] - y
                bx, by = (ring[2 * i + 2] - x) * kx, ring[2 * i + 3] - y
                dx, dy = bx - ax, by - ay
                L = dx * dx + dy * dy
                t = 0.0 if L == 0 else max(0.0, min(1.0, -(ax * dx + ay * dy) / L))
                px, py = ax + t * dx, ay + t * dy
                d2 = px * px + py * py
                if d2 < best:
                    best = d2
    return math.sqrt(best) * _KM_PER_DEG
