"""Download every public source used by CityPulse RainGuard and record a manifest.

Usage:
    python analysis/fetch_data.py            # core sources (~150 MB)
    python analysis/fetch_data.py --full     # also the 622 MB BMC Flood Preparedness Guidelines book
                                             # (only needed to re-digitise the ward incident map)

Every download is written to data/raw/ and logged in data/raw/manifest.json with its
URL, access timestamp (UTC), byte size and SHA-256 so that results can be traced back
to the exact file that produced them.

BMC and BEST PDFs are copyright of their publishers and are NOT redistributed in this
repository (data/raw/ is git-ignored); this script re-downloads them from the official
servers instead.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
USER_AGENT = "CityPulse-RainGuard/1.0 (HackAMatch 1.0 student prototype; non-commercial)"

DM = "https://dm.mcgm.gov.in/assets/pdf"
# Legacy 24 BMC wards. File names on the BMC server end in "-2021" but the content is the
# Flood Preparedness Guidelines 2026 ward directory (page footers say so).
WARD_CODES = ["A", "B", "C", "D", "E", "FN", "FS", "GN", "GS", "HE", "HW", "KE", "KW", "L",
              "ME", "MW", "N", "PN", "PS", "RC", "RN", "RS", "S", "T"]

SOURCES: list[dict] = [
    *[
        {"id": f"bmc_ward_{w}", "url": f"{DM}/All%20Ward/Ward%20{w}-2021.pdf",
         "file": f"bmc_fpg2026_ward/Ward_{w}.pdf", "group": "core"}
        for w in WARD_CODES
    ],
    {"id": "bmc_fpg2026_full", "url": f"{DM}/FPG%202021.pdf",
     "file": "bmc_fpg2026_full.pdf", "group": "full"},
    {"id": "best_dm_2026", "url": "https://www.bestundertaking.com/pdf/Disaster_Management_Protocol_Booklet_2026.pdf",
     "file": "best/Disaster_Management_Protocol_Booklet_2026.pdf", "group": "core"},
    {"id": "best_dm_2024_25", "url": "https://www.bestundertaking.com/pdf/Disaster_Management_Protocol_Booklet_2024_25.pdf",
     "file": "best/Disaster_Management_Protocol_Booklet_2024_25.pdf", "group": "core"},
    {"id": "best_dm_2023_24", "url": "https://www.bestundertaking.com/pdf/Disaster_Management_Protocol_Booklet_2023_24.pdf",
     "file": "best/Disaster_Management_Protocol_Booklet_2023_24.pdf", "group": "core"},
    {"id": "datameet_bmc_wards", "url": "https://raw.githubusercontent.com/datameet/Municipal_Spatial_Data/master/Mumbai/BMC_Wards.geojson",
     "file": "BMC_Wards.geojson", "group": "core"},
    {"id": "imd_monthly_opencity",
     "url": "https://data.opencity.in/dataset/c0e2f1ba-848a-4716-982b-d42636c44bf5/resource/3b1fcae7-b24f-431f-a259-64b56077acd5/download/6b7b0aed-e31d-433b-ba6d-b17b08a000df.csv",
     "file": "imd_mumbai_monthly_1901_2021.csv", "group": "core"},
    {"id": "census2011_opencity",
     "url": "https://data.opencity.in/dataset/1a81291d-369d-43e6-97b1-e62680434437/resource/fcfeacdc-aa80-4028-a468-f0267fa05d23/download/95e22d97-7f59-4214-b244-2abbf52e6027.csv",
     "file": "census2011_mumbai_wards.csv", "group": "core"},
]

# Two reference points: Santacruz (suburbs, IMD observatory location) and Colaba (island city).
RAIN_POINTS = {"santacruz": (19.0896, 72.8656), "colaba": (18.9067, 72.8147)}
RAIN_START, RAIN_END = "1991-01-01", "2025-12-31"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, dest: Path, retries: int = 3) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, headers={"User-Agent": USER_AGENT}, stream=True, timeout=300) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
                tmp.replace(dest)
                return
        except requests.RequestException as exc:
            if attempt == retries:
                raise
            print(f"  retry {attempt}: {exc}", file=sys.stderr)
            time.sleep(5 * attempt)


def open_meteo_archive_url(lat: float, lon: float) -> str:
    return ("https://archive-api.open-meteo.com/v1/archive"
            f"?latitude={lat}&longitude={lon}&start_date={RAIN_START}&end_date={RAIN_END}"
            "&daily=precipitation_sum&timezone=Asia%2FKolkata&models=era5")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="also fetch the 622 MB FPG 2026 book")
    ap.add_argument("--force", action="store_true", help="re-download files that already exist")
    args = ap.parse_args()

    manifest_path = RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    jobs = [s for s in SOURCES if s["group"] == "core" or args.full]
    for name, (lat, lon) in RAIN_POINTS.items():
        jobs.append({"id": f"open_meteo_era5_{name}", "url": open_meteo_archive_url(lat, lon),
                     "file": f"open_meteo_era5_daily_{name}.json", "group": "core"})

    for job in jobs:
        dest = RAW / job["file"]
        if dest.exists() and not args.force and job["id"] in manifest:
            print(f"skip  {job['id']} (cached)")
            continue
        print(f"fetch {job['id']}")
        download(job["url"], dest)
        manifest[job["id"]] = {
            "url": job["url"],
            "file": str(dest.relative_to(ROOT)).replace("\\", "/"),
            "accessed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "bytes": dest.stat().st_size,
            "sha256": sha256(dest),
        }
        manifest_path.write_text(json.dumps(manifest, indent=2))
        time.sleep(1)  # be polite to public servers

    print(f"manifest: {manifest_path} ({len(manifest)} entries)")


if __name__ == "__main__":
    main()
