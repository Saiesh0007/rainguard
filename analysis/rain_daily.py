"""Extract Mumbai's daily IMD rainfall from the 0.25 deg national grids, and check it.

Two grid cells cover Mumbai's land area:
  south  19.00 N 72.75 E  island city and inner suburbs (the same point as the IMD monthly series
                          from OpenCity used in rainfall.py, so the two can be cross-checked)
  north  19.25 N 72.75 E  northern suburbs (Borivali, Dahisar)
The 73.00 E cells are mostly Thane / Navi Mumbai and are not used.

City value: the wetter of the two cells ("heavy rain somewhere in Mumbai"). Days with a missing
value (-999 in the grid) stay missing; nothing is filled in.

Checks written to rain_daily_checks.json:
  * monthly sums of the south cell vs the OpenCity IMD monthly series (same point), overlap years
  * the 26 July 2005 storm, to confirm the date convention: the record rain of 26 July appears on
    27 July, so IMD's date D is the 24 hours ENDING 08:30 IST on D (08:30 D-1 to 08:30 D)

It also sums the archived Open-Meteo day-ahead forecast (fetch_rain_daily.py) over the same IMD rain
day (08:30 IST on D-1 to 08:30 IST on D), so predict.py needs only these small committed files.

If the raw grids are not on disk (they are 25 MB a year and not committed), the committed outputs are
kept and the step is skipped, so the pipeline still runs offline.

Outputs: data/processed/rain_daily_imd.csv, data/processed/rain_daily_checks.json,
         data/processed/forecast_day1_santacruz.csv
"""
from __future__ import annotations

import calendar
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
NLAT, NLON = 129, 135
CELLS = {"south": (19.00, 72.75), "north": (19.25, 72.75)}


def idx(lat: float, lon: float) -> tuple[int, int]:
    return round((lat - 6.5) / 0.25), round((lon - 66.5) / 0.25)


def read_year(path: Path, year: int) -> pd.DataFrame:
    ndays = 366 if calendar.isleap(year) else 365
    grid = np.fromfile(path, dtype="<f4").reshape(ndays, NLAT, NLON)
    out = pd.DataFrame({"date": pd.date_range(f"{year}-01-01", periods=ndays, freq="D")})
    for name, (lat, lon) in CELLS.items():
        j, i = idx(lat, lon)
        v = grid[:, j, i].astype(float)
        out[f"{name}_mm"] = np.where(v < -900, np.nan, v).round(1)
    return out


def forecast_days() -> None:
    raw = json.loads((RAW / "open_meteo_previous_runs_santacruz.json").read_text())
    h = pd.DataFrame({"time": pd.to_datetime(raw["hourly"]["time"]),
                      "fc_mm": raw["hourly"]["precipitation_previous_day1"]})
    # an hourly value is the rain in the hour BEFORE its timestamp, so 09:00 on D-1 ... 08:00 on D = IMD day D
    h["date"] = (h.time - pd.Timedelta(hours=9)).dt.normalize() + pd.Timedelta(days=1)
    g = h.groupby("date").fc_mm.agg(["sum", "count"])
    g = g[g["count"] == 24]["sum"].round(1).rename("forecast_day1_mm")
    g.to_csv(PROC / "forecast_day1_santacruz.csv", date_format="%Y-%m-%d")


def main() -> None:
    files = sorted((RAW / "imd_daily").glob("ind*_rfp25.grd"))
    if not files:
        print("raw IMD grids not found - keeping committed rain_daily_imd.csv (run fetch_rain_daily.py to rebuild)")
        return
    df = pd.concat([read_year(f, int(f.name[3:7])) for f in files], ignore_index=True)
    df["city_max_mm"] = df[["south_mm", "north_mm"]].max(axis=1, skipna=False)
    df.to_csv(PROC / "rain_daily_imd.csv", index=False, date_format="%Y-%m-%d")

    monthly = pd.read_csv(RAW / "imd_mumbai_monthly_1901_2021.csv")
    months = [m for m in monthly.columns if m[:3].lower() in {calendar.month_abbr[i].lower() for i in range(1, 13)}]
    long = monthly.melt(id_vars=[monthly.columns[0]], value_vars=months, var_name="m", value_name="opencity_mm")
    long["year"] = long.iloc[:, 0].astype(int)
    long["month"] = long.m.str[:3].str.lower().map({calendar.month_abbr[i].lower(): i for i in range(1, 13)})
    ours = df.assign(year=df.date.dt.year, month=df.date.dt.month).groupby(["year", "month"]).south_mm.sum(min_count=1)
    cmp = long.join(ours, on=["year", "month"]).dropna(subset=["south_mm", "opencity_mm"])
    jul05 = df.set_index("date").loc["2005-07-25":"2005-07-27"]
    checks = {
        "years": [int(df.date.dt.year.min()), int(df.date.dt.year.max())],
        "days": len(df),
        "missing_days": {c: int(df[c].isna().sum()) for c in ("south_mm", "north_mm")},
        "monthly_vs_opencity_same_point": {
            "n_months": len(cmp),
            "pearson_r": round(float(np.corrcoef(cmp.south_mm, cmp.opencity_mm)[0, 1]), 4),
            "median_abs_diff_mm": round(float((cmp.south_mm - cmp.opencity_mm).abs().median()), 1),
            "ratio_total": round(float(cmp.south_mm.sum() / cmp.opencity_mm.sum()), 3),
        },
        "jul_2005": {d.strftime("%Y-%m-%d"): {"south_mm": r.south_mm, "north_mm": r.north_mm}
                     for d, r in jul05.iterrows()},
        "jul_2005_reference": "BMC quotes 944 mm at Santacruz on 26 July 2005 (a point gauge; a 25 km cell averages it down)",
        "date_convention": "IMD date D = 24 h ending 08:30 IST on D (the 26 July 2005 storm is recorded on 27 July)",
    }
    (PROC / "rain_daily_checks.json").write_text(json.dumps(checks, indent=2))
    if (RAW / "open_meteo_previous_runs_santacruz.json").exists():
        forecast_days()
    else:
        print("archived forecasts not found - keeping committed forecast_day1_santacruz.csv")
    print(json.dumps(checks, indent=2))


if __name__ == "__main__":
    main()
