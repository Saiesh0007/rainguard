"""Download daily rainfall used by the heavy-rain outlook (analysis/predict.py).

Usage:
    python analysis/fetch_rain_daily.py            # IMD 1971-2025 + archived Open-Meteo forecasts

Sources
  IMD 0.25 deg daily gridded rainfall (Pai et al. 2014), one binary file per year from
  https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html (form POST to rainfall.php).
  Observed: a gridded analysis of rain-gauge data. 135 x 129 float32 grid, 365/366 days per file.
  The download page states no licence; it is used here for non-commercial research with citation.

  Open-Meteo Previous Runs API, "precipitation_previous_day1": the hourly forecast issued about
  one day earlier, for the Santacruz point. Archived from 2024 only (earlier years are null).
  CC BY 4.0, no key.

Each file is logged in data/raw/manifest.json (URL, access time, bytes, SHA-256), like fetch_data.py.
Only the small extracted Mumbai series (rain_daily.py) is committed; the 25 MB yearly grids are not.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_data import RAIN_POINTS, RAW, ROOT, USER_AGENT, sha256  # noqa: E402

IMD_URL = "https://www.imdpune.gov.in/cmpg/Griddata/rainfall.php"
IMD_YEARS = range(1971, 2026)
IMD_BYTES = {365: 365 * 135 * 129 * 4, 366: 366 * 135 * 129 * 4}
FC_START, FC_END = "2024-01-01", "2025-12-31"


def log(manifest: dict, src_id: str, url: str, dest: Path) -> None:
    manifest[src_id] = {
        "url": url,
        "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
        "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": dest.stat().st_size,
        "sha256": sha256(dest),
    }


def fetch_imd_year(year: int, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, 4):
        try:
            r = requests.post(IMD_URL, data={"rain": str(year)}, headers={"User-Agent": USER_AGENT}, timeout=600)
            r.raise_for_status()
            if len(r.content) not in IMD_BYTES.values():
                raise ValueError(f"unexpected size {len(r.content)} bytes")
            tmp = dest.with_suffix(".part")
            tmp.write_bytes(r.content)
            tmp.replace(dest)
            return
        except (requests.RequestException, ValueError) as exc:
            if attempt == 3:
                raise
            print(f"  retry {attempt}: {exc}", file=sys.stderr)
            time.sleep(10 * attempt)


def main() -> None:
    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text())

    for year in IMD_YEARS:
        src_id = f"imd_daily_025_{year}"
        dest = RAW / "imd_daily" / f"ind{year}_rfp25.grd"
        if dest.exists() and src_id in manifest:
            continue
        print(f"fetch {src_id}", flush=True)
        fetch_imd_year(year, dest)
        log(manifest, f"imd_daily_025_{year}", f"{IMD_URL} (POST rain={year})", dest)
        manifest_path.write_text(json.dumps(manifest, indent=2))
        time.sleep(2)  # be polite to a government server

    lat, lon = RAIN_POINTS["santacruz"]
    url = ("https://previous-runs-api.open-meteo.com/v1/forecast"
           f"?latitude={lat}&longitude={lon}&start_date={FC_START}&end_date={FC_END}"
           "&hourly=precipitation,precipitation_previous_day1&timezone=Asia%2FKolkata")
    dest = RAW / "open_meteo_previous_runs_santacruz.json"
    if not (dest.exists() and "open_meteo_previous_runs_santacruz" in manifest):
        print("fetch open_meteo_previous_runs_santacruz", flush=True)
        r = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
        r.raise_for_status()
        dest.write_bytes(r.content)
        log(manifest, "open_meteo_previous_runs_santacruz", url, dest)
        manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"manifest: {manifest_path} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()
