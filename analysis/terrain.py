"""Terrain context from the Copernicus GLO-90 DEM (served free by the Open-Meteo Elevation API).

1. A 500 m grid is laid over the BMC area (cell centres inside a ward polygon).
2. Elevation is fetched for every grid centre and every geocoded location.
3. tpi_m (topographic position index) = elevation minus the MEDIAN elevation of grid
   centres within 1 km (excluding the point's own cell). Negative = lower than its
   surroundings. Using the grid as the neighbourhood keeps API use to ~2,000 coordinates,
   well inside Open-Meteo's free limits (each coordinate counts as one call).

Caveats (repeated in docs/limitations.md): GLO-90 is a ~90 m *surface* model, so dense
buildings raise values; vertical error is several metres. TPI is used only as a coarse,
relative "is this place lower than its neighbourhood" signal, never as flood depth.

Responses are cached in data/processed/elevation_cache.json so re-runs are offline.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from shapely.geometry import Point, shape
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
CACHE = PROC / "elevation_cache.json"
WARDS = ROOT / "data" / "raw" / "BMC_Wards.geojson"
GRID_M = 500
NEIGHBOUR_M = 1000
USER_AGENT = "CityPulse-RainGuard/1.0 (HackAMatch 1.0 student prototype)"


def key(lat: float, lon: float) -> str:
    return f"{lat:.5f},{lon:.5f}"


def fetch_elevations(coords: list[tuple[float, float]], cache: dict) -> None:
    todo = sorted({key(*c) for c in coords} - cache.keys())
    print(f"  {len(todo)} coordinates to fetch ({len(coords)} requested)")
    for i in range(0, len(todo), 100):
        batch = todo[i:i + 100]
        params = {"latitude": ",".join(k.split(",")[0] for k in batch),
                  "longitude": ",".join(k.split(",")[1] for k in batch)}
        for attempt in range(15):
            r = requests.get("https://api.open-meteo.com/v1/elevation", params=params,
                             headers={"User-Agent": USER_AGENT}, timeout=60)
            if r.status_code != 429:
                break
            print("  rate-limited; waiting 5 minutes")
            time.sleep(300)
        r.raise_for_status()
        for k, e in zip(batch, r.json()["elevation"]):
            cache[k] = e
        CACHE.write_text(json.dumps(cache), encoding="utf8")
        time.sleep(1)


def build_grid() -> pd.DataFrame:
    gj = json.loads(WARDS.read_text(encoding="utf8"))
    wards = [(f["properties"]["name"], prep(shape(f["geometry"]))) for f in gj["features"]]
    minx, miny, maxx, maxy = 72.77, 18.88, 73.0, 19.28
    dlat = GRID_M / 111_320
    rows = []
    lat = miny + dlat / 2
    while lat < maxy:
        dlon = GRID_M / (111_320 * math.cos(math.radians(lat)))
        lon = minx + dlon / 2
        while lon < maxx:
            p = Point(lon, lat)
            for name, poly in wards:
                if poly.contains(p):
                    rows.append({"cell_id": f"g{len(rows):05d}", "lat": round(lat, 5), "lon": round(lon, 5),
                                 "ward": name})
                    break
            lon += dlon
        lat += dlat
    return pd.DataFrame(rows)


def local_xy(lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    return np.column_stack([lon * 111_320 * math.cos(math.radians(19.07)), lat * 111_320])


def tpi(points_xy: np.ndarray, points_elev: np.ndarray, grid_xy: np.ndarray, grid_elev: np.ndarray,
        exclude_self: bool) -> np.ndarray:
    out = np.full(len(points_xy), np.nan)
    for i, (xy, e) in enumerate(zip(points_xy, points_elev)):
        d = np.hypot(*(grid_xy - xy).T)
        mask = d <= NEIGHBOUR_M
        if exclude_self:
            mask &= d > 1  # drop the cell itself
        if mask.sum() >= 4:
            out[i] = e - np.median(grid_elev[mask])
    return np.round(out, 2)


def main() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf8")) if CACHE.exists() else {}
    grid = build_grid()
    loc = pd.read_csv(PROC / "geocoded_locations.csv").dropna(subset=["lat"])
    print(f"grid cells: {len(grid)}, geocoded records: {len(loc)}")
    coords = [(round(a, 5), round(b, 5)) for a, b in zip(grid.lat, grid.lon)] + \
             [(round(a, 5), round(b, 5)) for a, b in zip(loc.lat, loc.lon)]
    fetch_elevations(coords, cache)

    grid["elevation_m"] = [cache[key(round(a, 5), round(b, 5))] for a, b in zip(grid.lat, grid.lon)]
    gxy = local_xy(grid.lat.values, grid.lon.values)
    grid["tpi_m"] = tpi(gxy, grid.elevation_m.values, gxy, grid.elevation_m.values, exclude_self=True)
    grid.to_csv(PROC / "grid_terrain.csv", index=False)

    loc = loc[["record_id", "lat", "lon"]].copy()
    loc["elevation_m"] = [cache[key(round(a, 5), round(b, 5))] for a, b in zip(loc.lat, loc.lon)]
    loc["tpi_m"] = tpi(local_xy(loc.lat.values, loc.lon.values), loc.elevation_m.values, gxy,
                       grid.elevation_m.values, exclude_self=False)
    loc.to_csv(PROC / "location_terrain.csv", index=False)
    print(grid[["elevation_m", "tpi_m"]].describe().round(2))
    print(loc[["elevation_m", "tpi_m"]].describe().round(2))


if __name__ == "__main__":
    main()
