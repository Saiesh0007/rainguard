"""Package processed outputs into the static JSON files the web app reads.

Outputs:
  app/public/data/rainguard.json   locations, wards, findings, rainfall, evaluation, sources
  app/public/data/wards.geojson    simplified BMC ward boundaries (DataMeet, CC BY-SA 2.5 IN)

The app contains no hard-coded data values: every number it shows comes from here.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from shapely.geometry import mapping, shape

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
OUT = ROOT / "app" / "public" / "data"


def clean(v):
    if isinstance(v, float) and math.isnan(v):
        return None
    if hasattr(v, "item"):
        return clean(v.item())
    return v


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in r.items()} for r in df.to_dict(orient="records")]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RAW / "manifest.json").read_text())
    loc = pd.read_csv(PROC / "location_features.csv")
    scores = pd.read_csv(PROC / "priority_scores.csv")
    loc = loc.merge(scores, on="location_id", validate="one_to_one")
    loc = loc.merge(pd.read_csv(PROC / "diagnosis.csv", keep_default_na=False), on="location_id", validate="one_to_one")
    keep = ["location_id", "name", "detail", "ward", "sources", "n_sources", "record_ids", "in_bmc_fpg_2026",
            "in_best_annex_2026", "in_mtp_2026", "traffic_diversion", "lat", "lon", "geocode_precision", "geocode_osm_name", "geocode_note",
            "project_category", "pumps", "capacity_listed_m3hr", "capacity_complete", "elevation_m", "tpi_m",
            "tpi_pct_in_ward", "neighbours_1km", "incident_class", "incidents_low", "incidents_high",
            "incident_excess", "ward_burden", "ward_excess", "corroboration", "low_lying", "listing_density",
            "components_available", "priority_score", "priority_rank", "priority_tier", "top20_frequency",
            "rank_p10", "rank_p90", "plan_frequency", "diagnosis"]
    wards = pd.read_csv(PROC / "ward_stats.csv")

    def accessed(src_id: str) -> str | None:
        return manifest.get(src_id, {}).get("accessed_utc")

    sources = [
        {"id": "bmc_fpg2026", "name": "BMC Flood Preparedness Guidelines 2026 - ward directory",
         "publisher": "Brihanmumbai Municipal Corporation, Disaster Management Dept.",
         "url": "https://dm.mcgm.gov.in/", "accessed": accessed("bmc_ward_A"),
         "kind": "historical", "use": "Officially listed waterlogging spots, dewatering pumps; ward incident map",
         "terms": "BMC copyright; PDFs not redistributed - only derived facts with attribution."},
        {"id": "best_annex", "name": "BEST Disaster Management Protocol Booklet 2026, Annexure IX",
         "publisher": "BEST Undertaking (BMC)", "url": "https://www.bestundertaking.com/",
         "accessed": accessed("best_dm_2026"), "kind": "historical",
         "use": "Ward-wise low-lying flood-prone areas in the island city",
         "terms": "Public document; not redistributed - derived facts with attribution."},
        {"id": "mtp_diversions", "name": "Mumbai Traffic Police - traffic diversions during waterlogging",
         "publisher": "Mumbai Traffic Police, printed in BMC Flood Preparedness Guidelines 2026 (pp. 301-311)",
         "url": "https://dm.mcgm.gov.in/", "accessed": accessed("bmc_fpg2026_full"), "kind": "historical",
         "use": "Locations where traffic is diverted if waterlogging occurs, and the planned diversions",
         "terms": "BMC copyright; not redistributed - derived facts with attribution."},
        {"id": "datameet_wards", "name": "BMC ward boundaries", "publisher": "DataMeet (Pune chapter)",
         "url": "https://github.com/datameet/Municipal_Spatial_Data", "accessed": accessed("datameet_bmc_wards"),
         "kind": "context", "use": "Ward polygons, geocode checks, terrain grid", "terms": "CC BY-SA 2.5 India"},
        {"id": "imd_opencity", "name": "IMD gridded monthly rainfall, Mumbai grid point (1901-2021)",
         "publisher": "India Meteorological Department, via OpenCity", "url": "https://data.opencity.in/dataset/mumbai-rainfall-data",
         "accessed": accessed("imd_monthly_opencity"), "kind": "observed", "use": "Rainfall climatology and trend",
         "terms": "Listed by OpenCity as public domain (Government data)"},
        {"id": "imd_daily", "name": "IMD 0.25° daily gridded rainfall (1971-2025), two Mumbai cells",
         "publisher": "India Meteorological Department, Pune (Pai et al. 2014)",
         "url": "https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html", "accessed": accessed("imd_daily_025_2025"),
         "kind": "observed", "use": "Heavy-rain outlook: model training and chronological test; forecast track record",
         "terms": "No licence stated on the download page; used for non-commercial research with citation. Grids not redistributed."},
        {"id": "open_meteo_previous_runs", "name": "Open-Meteo archived day-ahead forecasts (2024-2025)",
         "publisher": "Open-Meteo Previous Runs API", "url": "https://open-meteo.com/en/docs/previous-runs-api",
         "accessed": accessed("open_meteo_previous_runs_santacruz"), "kind": "forecast (third-party)",
         "use": "Track record of the live forecast against observed IMD heavy-rain days", "terms": "CC BY 4.0"},
        {"id": "era5", "name": "ERA5 reanalysis daily precipitation (1991-2025)",
         "publisher": "ECMWF / Copernicus, via Open-Meteo Historical Weather API",
         "url": "https://open-meteo.com/en/docs/historical-weather-api", "accessed": accessed("open_meteo_era5_santacruz"),
         "kind": "estimated", "use": "Daily heavy-rain frequency; reliability check against IMD", "terms": "CC BY 4.0"},
        {"id": "dem", "name": "Copernicus GLO-90 DEM", "publisher": "ESA / Copernicus, via Open-Meteo Elevation API",
         "url": "https://open-meteo.com/en/docs/elevation-api", "accessed": None, "kind": "estimated",
         "use": "Elevation and relative elevation (TPI)", "terms": "Copernicus DEM licence; Open-Meteo CC BY 4.0"},
        {"id": "census2011", "name": "Census 2011 ward-wise population", "publisher": "ORGI, via OpenCity",
         "url": "https://data.opencity.in/dataset/mumbai-ward-wise-census-data", "accessed": accessed("census2011_opencity"),
         "kind": "observed", "use": "Population baseline for ward evaluation", "terms": "Listed by OpenCity as public domain"},
        {"id": "osm", "name": "OpenStreetMap via Nominatim (geocoding) and OpenFreeMap (basemap)",
         "publisher": "OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright",
         "accessed": None, "kind": "context", "use": "Geocoding of listed names; basemap tiles", "terms": "ODbL"},
        {"id": "open_meteo_forecast", "name": "Open-Meteo Forecast API (live, in the browser)",
         "publisher": "Open-Meteo", "url": "https://open-meteo.com/en/docs", "accessed": "live",
         "kind": "forecast (third-party)", "use": "Next-3-day rain outlook for Mumbai - shown as a third-party model forecast",
         "terms": "CC BY 4.0, free non-commercial use"},
    ]

    payload = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sources": sources,
        "locations": records(loc[keep].sort_values("priority_rank")),
        "wards": records(wards),
        "findings": json.loads((PROC / "eda_findings.json").read_text(encoding="utf8")),
        "rainfall": {
            "summary": json.loads((PROC / "rainfall_summary.json").read_text()),
            "climatology": records(pd.read_csv(PROC / "rainfall_monthly_climatology.csv")),
            "annual": records(pd.read_csv(PROC / "rainfall_annual_extremes.csv")),
        },
        "evaluation": json.loads((PROC / "evaluation.json").read_text()),
        "sensitivity": json.loads((PROC / "score_sensitivity.json").read_text()),
        "diagnosis": json.loads((PROC / "diagnosis_summary.json").read_text()),
        "allocation": json.loads((PROC / "allocation.json").read_text()),
        "outlook": json.loads((PROC / "outlook.json").read_text()),
        "cleaning": json.loads((PROC / "cleaning_log.json").read_text(encoding="utf8"))["outputs"],
        "verification": json.loads((PROC / "transcription_verification.json").read_text()),
    }
    (OUT / "rainguard.json").write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf8")

    gj = json.loads((RAW / "BMC_Wards.geojson").read_text(encoding="utf8"))
    feats = []
    for f in gj["features"]:
        geom = shape(f["geometry"]).simplify(0.0002, preserve_topology=True)
        feats.append({"type": "Feature", "properties": {"ward": f["properties"]["name"]},
                      "geometry": json.loads(json.dumps(mapping(geom), default=float))})
    (OUT / "wards.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                  separators=(",", ":")), encoding="utf8")
    print({p.name: p.stat().st_size for p in OUT.iterdir()})


if __name__ == "__main__":
    main()
