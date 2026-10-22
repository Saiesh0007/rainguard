"""Build ward-level and location-level feature tables from the cleaned inputs.

Outputs (data/processed/):
  ward_stats.csv          one row per legacy BMC ward
  location_features.csv   one row per unique location (from locations.csv) with terrain,
                          within-ward terrain percentiles and neighbour counts
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.geometry import shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TR = ROOT / "data" / "transcribed"
PROC = ROOT / "data" / "processed"
LOW_TPI_M = -2.0        # a grid cell this much lower than its 1 km neighbourhood counts as "low-lying"
NEIGHBOUR_RADIUS_M = 1000
PRECISE = {"point", "street"}


def ward_areas_km2() -> dict[str, float]:
    gj = json.loads((RAW / "BMC_Wards.geojson").read_text(encoding="utf8"))
    lat0 = math.radians(19.07)
    to_m = lambda x, y, z=None: (x * 111_320 * math.cos(lat0), y * 111_320)  # noqa: E731
    return {f["properties"]["name"]: transform(to_m, shape(f["geometry"])).area / 1e6 for f in gj["features"]}


def xy(lat, lon) -> np.ndarray:
    return np.column_stack([np.asarray(lon) * 111_320 * math.cos(math.radians(19.07)), np.asarray(lat) * 111_320])


def main() -> None:
    inc = pd.read_csv(PROC / "ward_incident_class.csv").set_index("ward")
    census = pd.read_csv(RAW / "census2011_mumbai_wards.csv")
    pop = census.groupby("Ward Name")["Total Population"].sum()
    grid = pd.read_csv(PROC / "grid_terrain.csv")
    loc = pd.read_csv(PROC / "locations.csv")
    fpg_counts = pd.read_csv(TR / "fpg2026_ward_section_counts.csv").groupby("ward_legacy").rows_listed.sum()
    best = pd.read_csv(TR / "best_annex_ix_2026.csv")
    best_counts = best.groupby("ward").size()
    mtp = pd.read_csv(TR / "mtp_fpg2026_diversions.csv")
    mtp_counts = mtp[mtp.is_location == "yes"].groupby("ward_legacy").size()
    areas = ward_areas_km2()

    wards = pd.DataFrame(index=sorted(areas))
    wards.index.name = "ward"
    wards["incident_class"] = inc.incident_class
    wards["incidents_low"] = inc.incidents_low
    wards["incidents_high"] = inc.incidents_high
    wards["population_2011"] = pop
    wards["area_km2"] = pd.Series(areas).round(2)
    wards["density_per_km2"] = (wards.population_2011 / wards.area_km2).round(0)
    wards["bmc_fpg2026_spots"] = fpg_counts.reindex(wards.index).fillna(0).astype(int)
    wards["best_annex_spots"] = best_counts.reindex(wards.index)  # NaN = ward outside BEST supply area
    wards["best_covers_ward"] = wards.best_annex_spots.notna() | wards.index.isin(
        ["A", "B", "C", "D", "E", "F/S", "F/N", "G/S", "G/N"])
    wards["mtp_diversion_rows"] = mtp_counts.reindex(wards.index).fillna(0).astype(int)
    wards["multi_source_locations"] = loc[loc.n_sources >= 2].groupby("ward").size().reindex(wards.index).fillna(0).astype(int)
    wards["unique_locations"] = loc.groupby("ward").size().reindex(wards.index).fillna(0).astype(int)
    g = grid.groupby("ward")
    wards["grid_cells"] = g.size()
    wards["median_elevation_m"] = g.elevation_m.median().round(1)
    wards["low_lying_share"] = g.tpi_m.apply(lambda s: float((s.dropna() <= LOW_TPI_M).mean())).round(3)
    assert wards.incident_class.notna().all() and wards.population_2011.notna().all()
    wards.to_csv(PROC / "ward_stats.csv")

    # ---- location features ----
    terr = pd.read_csv(PROC / "location_terrain.csv")
    terr_by_xy = {(round(a, 5), round(b, 5)): (e, t) for a, b, e, t in
                  zip(terr.lat, terr.lon, terr.elevation_m, terr.tpi_m)}
    loc["elevation_m"] = [terr_by_xy.get((round(a, 5), round(b, 5)), (np.nan, np.nan))[0] if pd.notna(a) else np.nan
                          for a, b in zip(loc.lat, loc.lon)]
    loc["tpi_m"] = [terr_by_xy.get((round(a, 5), round(b, 5)), (np.nan, np.nan))[1] if pd.notna(a) else np.nan
                    for a, b in zip(loc.lat, loc.lon)]
    # within-ward percentile of the location's TPI / elevation among that ward's grid cells
    tpi_pct, elev_pct = [], []
    for r in loc.itertuples():
        cells = grid[grid.ward == r.ward]
        if pd.isna(r.tpi_m) or cells.empty:
            tpi_pct.append(np.nan)
            elev_pct.append(np.nan)
            continue
        tpi_pct.append(float((cells.tpi_m.dropna() < r.tpi_m).mean()))
        elev_pct.append(float((cells.elevation_m < r.elevation_m).mean()))
    loc["tpi_pct_in_ward"] = np.round(tpi_pct, 3)
    loc["elev_pct_in_ward"] = np.round(elev_pct, 3)

    mapped = loc.lat.notna()
    pts = xy(loc.lat.fillna(0), loc.lon.fillna(0))
    neigh = []
    for i in range(len(loc)):
        if not mapped.iloc[i]:
            neigh.append(np.nan)
            continue
        d = np.hypot(*(pts[mapped.values] - pts[i]).T)
        neigh.append(int((d <= NEIGHBOUR_RADIUS_M).sum() - 1))
    loc["neighbours_1km"] = neigh
    loc = loc.join(wards[["incident_class", "incidents_low", "incidents_high"]], on="ward")
    loc.to_csv(PROC / "location_features.csv", index=False, encoding="utf8")
    print(wards.to_string())
    print(loc[["elevation_m", "tpi_m", "tpi_pct_in_ward", "neighbours_1km"]].describe().round(2))


if __name__ == "__main__":
    main()
