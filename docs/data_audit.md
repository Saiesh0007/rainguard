# Data feasibility audit

**Audit date:** 22 October 2026. Every URL below was accessed on this date. Exact access times and SHA-256 hashes for every downloaded file are in [`data/raw/manifest.json`](../data/raw/manifest.json).

The rule was: confirm each source exists, is free, and is usable on its terms *before* building anything on it. Sources that failed are listed too, because they explain why RainGuard does not forecast.

## 1. Sources used

### 1.1 BMC Flood Preparedness Guidelines 2026 (FPG 2026): ward directory
| | |
|---|---|
| Publisher | Brihanmumbai Municipal Corporation (BMC), Disaster Management Department |
| URL | `https://dm.mcgm.gov.in/assets/pdf/All%20Ward/Ward%20<W>-2021.pdf` (24 files) and the full book `https://dm.mcgm.gov.in/assets/pdf/FPG%202021.pdf` (622 MB, 319 pp.) |
| Note on file names | The server file names say "2021" and "FPG 2021", but every page footer reads *Flood Preparedness Guidelines 2026*, and the PDF was modified on 19 June 2026. |
| Contains | Per ward: "List of Water Logging Spots" (location, project category, number of dewatering pumps, pump capacity, pump-operator phone). |
| Type | **Historical / official listing.** It names places, with no dates of flooding events. |
| Coverage | All 24 legacy wards. BMC now publishes P/North as P/East + P/West and K/East as K/South + K/North. |
| Format / quality | Scanned images (no text layer). Headers state a row count, which serves as a checksum. 3 sections disagree with their own header (P/East 4 vs 5 rows, R/N 5 vs 6, C has no number); P/S numbers its rows 1, 2, 3, 6; one within-ward duplicate (Shastri Nagar, Vidyavihar East). Several multi-pump rows give only one capacity value. |
| Terms | Page 2: "sole copyright of the Brihanmumbai Municipal Corporation … no part … may be reproduced … without prior permission". **We do not redistribute the PDFs.** We publish only derived factual fields (location names, ward, pump counts) with attribution, for non-commercial research. Phone numbers are excluded. Judges can re-download the PDFs with `analysis/fetch_data.py`. |
| Used for | 97 location rows; pump/mitigation context. |

### 1.2 BMC FPG 2026, page 18: ward-wise waterlogging incidents map
| | |
|---|---|
| Contains | Choropleth "Water Logging – Ward-wise no. of incidents", 7 bins (0–115 … 467–800); "Source: GIS (derived from CCS)". |
| Type | **Historical, ward-level, binned.** These are incident/complaint records, not exact counts. |
| Period | **Ambiguous.** The page caption says 2016–2025; the legend inside the embedded image says 2016–2023. Both are kept and disclosed. |
| Method | Digitised by colour-matching 3 hand-placed sample points per ward to the 7 legend swatches (`analysis/digitize_ward_incidents.py`). All 24 wards were unanimous. A QC image is written to `data/processed/qc_ward_incident_digitisation.png`. |
| Terms | As 1.1. |

### 1.3 Mumbai Traffic Police diversion table (printed in FPG 2026, pp. 301–311)
| | |
|---|---|
| Contains | "If water logging occurs at → Traffic will be diverted to", grouped under ward headings for 19 of the 24 legacy wards (none for D, R/C, R/N, R/S, T). |
| Type | **Historical / official plan.** These are places where waterlogging is expected; they are not dated events. |
| Quality | Has a text layer (all 92 rows verified). 2 rows are not locations ("Traffic from North side", "Dadar Traffic") and are excluded with reasons. One duplicate (J J Marg police station). Ward headings are police groupings: 2 precisely geocoded rows fall in a different BMC ward and were re-assigned (logged). |
| Terms | As 1.1. |

### 1.4 BEST Disaster Management Protocol Booklets: Annexure IX
| | |
|---|---|
| Publisher | BEST Undertaking (a BMC undertaking) |
| URLs | `https://www.bestundertaking.com/pdf/Disaster_Management_Protocol_Booklet_2026.pdf`, `…_2024_25.pdf`, `…_2023_24.pdf` |
| Contains | "Ward wise identified low lying flooding prone areas" (84 rows), used by BEST to switch off electricity safely. |
| Coverage | Only BEST's electricity area: the 9 island-city wards A, B, C, D, E, F/S, F/N, G/S, G/N. |
| Type | **Historical / official listing**, undated. |
| Quality | Text layer; 83/84 rows verified automatically (the 84th fails only on a line-wrap). One exact duplicate (rows 42/43). **The list is essentially unchanged across editions** (word-level similarity 0.989 for 2023-24 vs 2024-25 and 0.974 for 2024-25 vs 2026; differences are typographic), so edition persistence carries no information. Rows 5, 6 and 8 use residents' names as landmarks; **these names are redacted** in our transcription. |
| Terms | Public document; not redistributed. Derived facts only, with attribution. |

### 1.5 DataMeet: BMC ward boundaries
| | |
|---|---|
| URL | `https://github.com/datameet/Municipal_Spatial_Data/blob/master/Mumbai/BMC_Wards.geojson` |
| Licence | **CC BY-SA 2.5 India** (stated in `Mumbai/Readme.md`; the repository default is CC BY 4.0). Attribution: DataMeet Pune chapter. |
| Coverage | 24 legacy wards (WGS84). These predate the 2024–26 ward splits. |
| Used for | Ward checks on geocodes, terrain grid, map. |

### 1.6 IMD gridded monthly rainfall for Mumbai (via OpenCity)
| | |
|---|---|
| URL | `https://data.opencity.in/dataset/mumbai-rainfall-data` (CSV) |
| Contains | Monthly rainfall (mm), 1901–2021, for IMD grid point 19.00 N 72.75 E. |
| Type | **Observed** (gridded analysis of rain-gauge data). |
| Licence | OpenCity lists it as "Other (Public Domain)", source IMD. |
| Quality | No missing values; the monthly values sum to the published annual totals (checked in code). It is monthly only, so it cannot be linked to events. |

### 1.7 ERA5 reanalysis daily precipitation (via Open-Meteo Historical Weather API)
| | |
|---|---|
| URL | `https://archive-api.open-meteo.com/v1/archive?…&daily=precipitation_sum&models=era5` |
| Licence | CC BY 4.0; free for non-commercial use, no API key. |
| Type | **Estimated** (model reanalysis, about 25 km). |
| Coverage | 1991-01-01 to 2025-12-31, 12,784 days, no gaps (checked). |
| Key limitation | **Santacruz and Colaba resolve to the same ERA5 cell (19.0 N 73.0 E), so the two series are identical.** There is no within-city rainfall signal. ERA5 shows **69.6 mm** for 26 July 2005, when BMC quotes **944 mm** at Santacruz, and ERA5 annual totals are 80% of IMD's (1991–2021). |

### 1.8 Copernicus GLO-90 DEM (via Open-Meteo Elevation API)
| | |
|---|---|
| Type | **Estimated.** A 90 m digital *surface* model (includes buildings), with integer metres. |
| Use | Elevation and relative elevation (TPI) for 1,841 grid cells (500 m) and every geocoded record. |
| Limits | The free API counts each coordinate as a call (5,000/hour). The first design (8-point rings per cell, about 16,000 calls) hit the hourly limit, so TPI is now computed from neighbouring grid cells (about 2,100 calls). Responses are cached in `data/processed/elevation_cache.json`. |

### 1.9 Census 2011 ward population (via OpenCity)
CSV of census wards with BMC ward names. The aggregated total of **12,442,373** matches the official Greater Mumbai 2011 figure. Listed as public domain. It is 15 years old.

### 1.10 OpenStreetMap: Nominatim geocoding and OpenFreeMap tiles
* Nominatim usage policy: max 1 request/s, identifying User-Agent, cache results, small one-off batches only. We made one batch of 279 distinct queries, cached in `data/processed/geocode_cache.json`; the app itself never calls Nominatim. Data is ODbL.
* OpenFreeMap: free, no key, no view limits; attribution "© OpenMapTiles, Data from OpenStreetMap" is shown by MapLibre.

### 1.11 Open-Meteo Forecast API (live, in the browser)
A third-party 3-day precipitation forecast for one Mumbai point. CC BY 4.0, free for non-commercial use, no key. It is shown as a **third-party forecast**, never as a RainGuard prediction, with stale/offline states.

### 1.12 IMD 0.25° daily gridded rainfall (added 23 October 2026)
| | |
|---|---|
| Publisher | India Meteorological Department, Pune (Pai et al. 2014, *Mausam* 65(1)) |
| URL | `https://www.imdpune.gov.in/cmpg/Griddata/Rainfall_25_Bin.html` (one binary file per year, form POST to `rainfall.php`) |
| Contains | Daily rain (mm) on a 135 × 129 grid over India, 1901–2025. We download 1971–2025 and keep two cells: 19.00 N 72.75 E (island city, inner suburbs) and 19.25 N 72.75 E (northern suburbs). |
| Type | **Observed** (gridded analysis of rain-gauge data). |
| Quality | The 19.00 N 72.75 E monthly sums **equal the OpenCity IMD monthly series exactly** (it is the same grid point), checked in `rain_daily_checks.json`. Still a 25 km cell average, so it under-states point extremes. |
| Terms | The download page states no licence. Used for non-commercial research with citation; the grids are not redistributed, only the extracted two-cell series (`data/processed/rain_daily_imd.csv`). |
| Used for | The heavy-rain outlook (`analysis/predict.py`): training, chronological test, and the observed side of the forecast track record. |

### 1.13 Open-Meteo Previous Runs API: archived day-ahead forecasts (added 23 October 2026)
`precipitation_previous_day1` for the Santacruz point: the hourly forecast issued about one day earlier. **Archived only from 2024** (earlier years return nulls, checked for 2021–2023). CC BY 4.0, no key. Used only to measure the live forecast's track record against IMD over the 2024 and 2025 monsoons.

## 2. Sources checked and rejected

| Source | Finding | Decision |
|---|---|---|
| **OpenStreetMap `flood_prone=*` / `hazard=flood` tags** (Overpass, Mumbai bbox) | Only 4 features, all in Thane (outside BMC). | Not usable. |
| **data.gov.in** | No Mumbai waterlogging-spot dataset found. | Not used. |
| **OpenCity "flooding locations"** | Exists for Bengaluru, Hyderabad and Chennai; none for Mumbai. | Not available. |
| **BMC DM portal live rain gauges** (`dmwebtwo.mcgm.gov.in/api`) | The portal shows 120 automatic rain gauges, but the API needs authentication. Credentials are embedded in the public JavaScript bundle, but **using them would bypass access control**. | Not used. This is a genuine blocker for neighbourhood-level rainfall. |
| **BMC `List_of_Incidents.pdf`** | Only a taxonomy of incident types, with no records. | Not useful. |
| **BMC ward DM plans 2021 / city DM plan** | The "2021" files are the 2026 ward directory (used above). The 700 MB city plan is scanned and duplicates it. | Covered by 1.1. |
| **IMD station data (mausam.imd.gov.in)** | No free, bulk, machine-readable daily station download for Santacruz/Colaba. | Used the IMD gridded monthly data instead (1.6). |
| **Research datasets** (crowdsourced Twitter flood maps, MCGM flooding-site lists used in papers) | Data not published, or licence unknown. | Not used. |
| **Social media / news** | Not verified ground truth (Project.md §5). | Not used. |
| **Official city disruption-day calendar** (checked 23 Oct 2026): railway suspensions, BMC rain holidays | No official, dated archive found. Central Railway and BMC statements survive mainly as quotes in news reports, which are not ground truth here. | Not built. The outlook therefore predicts heavy rain, not disruption. |
| **Tide records** (checked 23 Oct 2026) | PSMSL Mumbai (Apollo Bandar, station 43) is **monthly mean sea level**, not daily high tides. BMC FPG 2026 (pp. 19–20) gives only *monthly counts* of days with tide > 4.5 m (18–28 a season, 2016–2025) and of days with rain > 100 mm **and** tide > 4.5 m (at most 5 a year, 0 in 7 of 10 years). Daily high-tide dates appear mostly in news reports. | Not used as a feature: no dated series, and too few coincidences to validate. BMC's counts are quoted as context. |

## 3. Feasibility decision

**Risk prioritisation is feasible; location-level forecasting is not. A city-wide heavy-rain outlook is feasible and is tested chronologically (added 23 Oct 2026, §1.12).**

* There are **no dated, located waterlogging events** in any free, lawful public source. Without a target label over time, no forecast can be trained or validated chronologically.
* Incident history exists only as a **binned, ward-level, single-period map**. This allows a cross-sectional ward analysis (n = 24), but nothing at event level.
* Free rainfall is **monthly (IMD)** or **one 25 km model cell (ERA5)** that badly under-estimates extremes. It cannot distinguish neighbourhoods, and the city's 120-gauge network is not openly accessible.
* What *is* available supports an honest product. Three independent official lists name **251 distinct places**, which can be mapped, explained and prioritised transparently, alongside verified rainfall context and a clearly labelled third-party forecast.

**What would enable forecasting:** BMC's dated waterlogging complaints (CCS) with locations, and open access to its 15-minute automatic rain-gauge and tide records. With 3+ monsoons of these, a chronological, location-level model (event vs no event, given rain intensity and tide) could be validated with precision/recall against a rain-threshold baseline.
