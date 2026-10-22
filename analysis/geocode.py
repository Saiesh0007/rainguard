"""Geocode transcribed locations with OpenStreetMap Nominatim, then quality-check them.

Nominatim usage policy is respected: one request per second, an identifying User-Agent,
a one-off batch (~200 queries), and every response cached in
data/processed/geocode_cache.json (committed) so re-runs never hit the server again.

Each record gets:
  * geocode_precision: "point" (a specific feature: station, junction, building, short road),
                       -- results of the neighbourhood fallback query (query_2), or of a
                       query_1 marked query_1_level=area, are always "area" so that a
                       station or bus stop sharing the neighbourhood's name is never
                       mistaken for the spot itself;
                       "street" (a longer road; location is somewhere along it),
                       "area" (a neighbourhood/suburb centroid), or "not_found".
  * ward_check: "inside" the legacy BMC ward the source assigns it to (300 m tolerance for
                boundary roads), "outside" (the geocode contradicts the source -> not mapped
                as a point), "reassigned" (Mumbai Traffic Police rows only: their ward
                headings are police groupings, so a specific-feature geocode outside the
                heading's ward is kept and assigned to the ward that contains it), or "n/a".
Only records with ward_check == "inside" are drawn on the map as points.
"""
from __future__ import annotations

import json
import math
import time
from pathlib import Path

import pandas as pd
import requests
from shapely.geometry import Point, shape
from shapely.ops import transform

ROOT = Path(__file__).resolve().parents[1]
TR = ROOT / "data" / "transcribed"
PROC = ROOT / "data" / "processed"
CACHE = PROC / "geocode_cache.json"
WARDS = ROOT / "data" / "raw" / "BMC_Wards.geojson"
USER_AGENT = "CityPulse-RainGuard/1.0 (HackAMatch 1.0 student prototype; one-off geocoding)"
VIEWBOX = "72.76,19.29,73.01,18.88"  # Greater Mumbai bounding box (lon1,lat1,lon2,lat2)
BOUNDARY_TOLERANCE_M = 300
AREA_TYPES = {"suburb", "neighbourhood", "quarter", "city_district", "residential", "village",
              "hamlet", "locality", "city", "town", "administrative", "postcode", "isolated_dwelling"}


def bbox_diag_m(bb: list[str]) -> float:
    s, n, w, e = map(float, bb)
    dy = (n - s) * 111_320
    dx = (e - w) * 111_320 * math.cos(math.radians((n + s) / 2))
    return math.hypot(dx, dy)


def nominatim(query: str, cache: dict) -> list[dict]:
    if query in cache:
        return cache[query]
    r = requests.get("https://nominatim.openstreetmap.org/search",
                     params={"q": query, "format": "jsonv2", "limit": 3, "countrycodes": "in",
                             "viewbox": VIEWBOX, "bounded": 1, "addressdetails": 0},
                     headers={"User-Agent": USER_AGENT}, timeout=60)
    r.raise_for_status()
    cache[query] = r.json()
    CACHE.write_text(json.dumps(cache, indent=1, ensure_ascii=False), encoding="utf8")
    time.sleep(1.1)
    return cache[query]


def precision_of(hit: dict) -> str:
    diag = bbox_diag_m(hit["boundingbox"])
    if hit.get("type") in AREA_TYPES or hit.get("category") == "place" or diag > 2500:
        return "area"
    if hit.get("category") == "highway" and diag > 400:
        return "street"
    return "point"


def load_wards() -> dict:
    gj = json.loads(WARDS.read_text(encoding="utf8"))
    # metres-ish local projection for buffering (equirectangular around Mumbai)
    lat0 = math.radians(19.07)
    to_m = lambda x, y, z=None: (x * 111_320 * math.cos(lat0), y * 111_320)  # noqa: E731
    return {f["properties"]["name"]: transform(to_m, shape(f["geometry"])) for f in gj["features"]}, to_m


def main() -> None:
    cache = json.loads(CACHE.read_text(encoding="utf8")) if CACHE.exists() else {}
    fpg = pd.read_csv(TR / "bmc_fpg2026_waterlogging_spots.csv")
    best = pd.read_csv(TR / "best_annex_ix_2026.csv")
    mtp = pd.read_csv(TR / "mtp_fpg2026_diversions.csv")
    mtp = mtp[mtp.is_location == "yes"]
    queries = pd.read_csv(TR / "geocode_queries.csv").set_index("record_id")
    wards, to_m = load_wards()

    records = [(r.record_id, r.ward_legacy, False) for r in fpg.itertuples()] + \
              [(r.record_id, r.ward, False) for r in best.itertuples()] + \
              [(r.record_id, r.ward_legacy, True) for r in mtp.itertuples()]
    rows = []
    for rid, ward, heading_only in records:
        chosen = None
        for qcol in ("query_1", "query_2"):
            q = queries.at[rid, qcol]
            if pd.isna(q):
                continue
            hits = nominatim(q, cache)
            # prefer the first hit that falls inside the expected ward
            for h in hits:
                pt = Point(*to_m(float(h["lon"]), float(h["lat"])))
                inside = wards[ward].buffer(BOUNDARY_TOLERANCE_M).contains(pt)
                if inside:
                    chosen = (q, qcol, h, "inside")
                    break
            if chosen:
                break
            if (heading_only and hits and qcol == "query_1"
                    and queries.at[rid, "query_1_level"] == "feature" and precision_of(hits[0]) != "area"):
                h = hits[0]
                pt = Point(*to_m(float(h["lon"]), float(h["lat"])))
                actual = next((w for w, poly in wards.items() if poly.contains(pt)), None)
                if actual:
                    chosen = (q, qcol, h, "reassigned")
                    ward = actual
                    break
            if hits and chosen is None and qcol == "query_2":
                h = hits[0]
                chosen = (q, qcol, h, "outside")
        if chosen is None:
            rows.append({"record_id": rid, "ward_legacy": ward, "geocode_query": None, "query_used": None,
                         "lat": None, "lon": None, "osm_type": None, "osm_class": None, "osm_name": None,
                         "geocode_precision": "not_found", "ward_check": "n/a"})
            continue
        q, qcol, h, check = chosen
        rows.append({
            "record_id": rid, "ward_legacy": ward, "geocode_query": q, "query_used": qcol,
            "lat": round(float(h["lat"]), 6), "lon": round(float(h["lon"]), 6),
            "osm_type": h.get("type"), "osm_class": h.get("category"), "osm_name": h.get("display_name"),
            "geocode_precision": ("area" if qcol == "query_2" or queries.at[rid, "query_1_level"] == "area"
                                  else precision_of(h)),
            "ward_check": check,
        })
    out = pd.DataFrame(rows)
    # Manual review (data/transcribed/geocode_review.csv) may only DOWNGRADE precision
    # (point -> street -> area); it never moves a coordinate.
    rank = {"point": 0, "street": 1, "area": 2, "not_found": 3}
    review = pd.read_csv(TR / "geocode_review.csv").set_index("record_id")
    out["review_note"] = None
    for i, r in out.iterrows():
        if r.record_id in review.index:
            new = review.at[r.record_id, "reviewed_precision"]
            if rank[new] < rank[r.geocode_precision]:
                raise ValueError(f"review for {r.record_id} would upgrade precision")
            out.at[i, "geocode_precision"] = new
            out.at[i, "review_note"] = review.at[r.record_id, "reason"]
    out.to_csv(PROC / "geocoded_locations.csv", index=False, encoding="utf8")
    print(out.groupby(["geocode_precision", "ward_check"]).size())
    print("query fallback used:", int((out.query_used == "query_2").sum()))


if __name__ == "__main__":
    main()
