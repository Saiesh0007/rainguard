# Data statement

Submission requirement: dataset links, access dates, licence/terms, fields used and preprocessing. Full details are in [`data_audit.md`](data_audit.md). Access times and hashes are in [`data/raw/manifest.json`](../data/raw/manifest.json). Sources were accessed on **22 October 2026**, except the IMD daily grids and archived forecasts, accessed on **23 October 2026**.

| Dataset | Link | Licence / terms | Fields used | Preprocessing |
|---|---|---|---|---|
| BMC Flood Preparedness Guidelines 2026: ward directory (24 PDFs) | dm.mcgm.gov.in/assets/pdf/All Ward/Ward &lt;W&gt;-2021.pdf | BMC copyright; not redistributed; derived facts used with attribution | ward, location of waterlogging spot, project category, no. of dewatering pumps, pump capacity (phone numbers **excluded**) | Manual transcription → OCR verification (93/97 auto-matched, rest checked by eye) → legacy-ward mapping → geocoding → de-duplication |
| BMC FPG 2026, p.18: ward incident map | dm.mcgm.gov.in/assets/pdf/FPG 2021.pdf | as above | colour class per ward | Colour-matched to the legend (3 points per ward, 24/24 unanimous) → ordinal class 1–7 |
| Mumbai Traffic Police diversions (FPG 2026, pp.301–311) | as above | as above | location, diversion route, ward heading | Manual transcription (92/92 verified); 2 non-location rows excluded; geocoded; 2 rows re-assigned to their true ward |
| BEST DM Protocol Booklets 2023-24, 2024-25, 2026: Annexure IX | bestundertaking.com/pdf/Disaster_Management_Protocol_Booklet_*.pdf | public document; not redistributed | ward, road/area, location | Manual transcription (83/84 verified); residents' names redacted; edition comparison |
| DataMeet BMC wards | github.com/datameet/Municipal_Spatial_Data (Mumbai/BMC_Wards.geojson) | CC BY-SA 2.5 IN | ward name, geometry | Simplified (0.0002°) for the app |
| IMD gridded monthly rainfall (1901–2021) | data.opencity.in/dataset/mumbai-rainfall-data | Public domain (per OpenCity) | Year, monthly mm | Long format; checked monthly values sum to annual totals |
| IMD 0.25° daily gridded rainfall (1971–2025) | imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html | No licence stated; non-commercial research use with citation (Pai et al. 2014); grids not redistributed | daily mm at 19.00 N/19.25 N, 72.75 E | Extracted two cells; no missing days; monthly sums checked against the OpenCity IMD series (same point, r = 0.995, median difference 0 mm); city value = wetter cell; date convention checked with 26 July 2005 |
| Open-Meteo archived day-ahead forecasts (2024–2025) | previous-runs-api.open-meteo.com | CC BY 4.0 | hourly precipitation_previous_day1, Santacruz | Summed over the IMD rain day (08:30–08:30 IST); only complete 24-hour days kept |
| ERA5 daily precipitation (1991–2025) | archive-api.open-meteo.com | CC BY 4.0 | date, precipitation_sum | Gap check; annual extremes by IMD category |
| Copernicus GLO-90 DEM | api.open-meteo.com/v1/elevation | Copernicus DEM licence / CC BY 4.0 | elevation | 500 m grid; TPI vs 1 km neighbours |
| Census 2011 ward population | data.opencity.in/dataset/mumbai-ward-wise-census-data | Public domain (per OpenCity) | Ward Name, Total Population | Summed by ward (total 12,442,373) |
| OpenStreetMap via Nominatim | nominatim.openstreetmap.org | ODbL | lat, lon, type, display name | One cached batch (279 queries, 1 req/s); ward check; manual precision downgrades |
| OpenFreeMap tiles | tiles.openfreemap.org | free; OpenMapTiles + OSM attribution | basemap | — |
| Open-Meteo forecast (live) | api.open-meteo.com/v1/forecast | CC BY 4.0, non-commercial | daily precipitation_sum, probability | Labelled with IMD categories; cached with stale flag |

**Missing values:** never imputed. Missing pump data shows as "none listed" or "unknown". Missing terrain (area-level places) is excluded from the score. **Duplicates:** 3 within-source duplicates merged; 18 cross-source matches merged; 2 matches rejected on review; 1 ambiguous match skipped. **Outliers:** none removed. Elevation outliers (hills up to 473 m) are real terrain, and TPI is used as a within-ward percentile, so they do not dominate.

**Synthetic data:** none. The app shows only real processed outputs. Tests use real exported data plus small inline fixtures for forecast parsing, which are labelled in the test code.
