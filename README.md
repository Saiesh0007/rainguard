# CityPulse RainGuard

**Evidence-backed waterlogging awareness for Mumbai.** HackAMatch 1.0 · CityPulse: *Predict. Explain. Act.*

RainGuard combines **three official 2026 lists of waterlogging-prone places** in Mumbai (BMC, BEST, Mumbai Traffic Police), BMC's ward incident history, IMD and ERA5 rainfall, and terrain into a mobile-first map. Every assessment shows its evidence, precision and limitations.

**Primary user:** a BMC ward engineer or disaster-management officer deciding *which places their teams inspect this week, what to check there, and whether tomorrow is likely to be a heavy-rain day*. Residents and commuters get the map and cautious, practical guidance.

> **Feasibility decision:** location-level *waterlogging forecasting* is **not** supported by free public data. There are no dated, located waterlogging events, and no open neighbourhood-scale rainfall. RainGuard therefore prioritises places with transparent rules, and predicts only what can be tested: a **city-wide heavy-rain outlook** for tomorrow, validated on 2017–2025 against two baselines. See [`docs/data_audit.md`](docs/data_audit.md).

## What's inside

| | |
|---|---|
| 🗺 **Map** | 251 distinct official places (236 mappable). Exact places are dots; neighbourhood-only places are hollow rings. Ward incident-history shading, search, an accessible list view, and a live 3-day rain outlook labelled as a third-party forecast. |
| 🔎 **Evidence panel** | Each block is labelled *Observed / Historical / Estimated / Forecast / Unknown*. Shows the lists naming the place, the traffic diversion plan, ward incident class, geocode precision, terrain (unvalidated), pumps, and "what you can do". |
| 📊 **Insights** | Six findings computed from the data, each with method, period, sample, caveats and an interactive chart or table. |
| 🏛 **Plan** | Weekly inspection plan: K places, at most N per ward, each with **what to check** (rule-based labels: no pump recorded, missing from BMC's list, traffic diversion, exact spot unknown, named by 2+ lists) and how often it stays in the plan under other weightings. Live weight sliders, a one-click population-adjusted view, filters, and CSV downloads. |
| ⓘ **Method** | Sources and terms, preparation steps, ward-level evaluation table, sensitivity, limitations. |

## Key findings (all computed by `analysis/eda.py`)
1. **F2:** The three official lists name **251 distinct places, but only 16 (6%) appear on more than one.** BMC's 2026 list says wards A, B and G/N have no spots; BEST lists 16 there. BEST's list is essentially unchanged since 2023-24.
2. **F1:** 10 of 15 suburban wards (but only 2 of 9 island-city wards) are in the two highest incident classes. **Ward population alone ranks wards with ρ = 0.835**, and a population-only baseline predicts the incident class with leave-one-out MAE 0.73 vs 1.92 for the median baseline. Terrain adds nothing measurable.
3. **F3:** 94.7% of Mumbai's rain falls in June–September (IMD 1901–2021). Annual rain rose by about 49 mm per decade (p = 0.0004). **ERA5 reanalysis shows 69.6 mm on 26 July 2005**, when 944 mm was recorded at Santacruz.
4. **F4:** Precisely located listed places are **not significantly lower** than the rest of their ward on a 90 m DEM (p = 0.17, n = 92), so terrain is off by default in the score.
5. **F5:** 43 of 97 BMC-listed spots have no dewatering pump recorded against them.
6. **F6:** After a heavy-rain day (IMD ≥ 64.5 mm), the next day is heavy **43%** of the time, against 6% otherwise (1971–2016). The heavy-rain outlook built on this beats the monthly and persistence baselines on 2017–2025: **Brier skill 0.22 (95% CI 0.20–0.24), AUC 0.85**. The live forecast's own "heavy" call caught only 5 of 33 heavy days in 2024–25, so the app quotes how often each forecast band was followed by a heavy day.

Full results: [`docs/evaluation.md`](docs/evaluation.md).

## Quick start

Requirements: Python ≥ 3.11, Node ≥ 20. Optional: [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki), used only to re-verify the scanned BMC tables.

```bash
# 1. Analysis pipeline (geocodes and elevations are cached in the repo, so this runs offline)
pip install -r requirements.txt
python analysis/fetch_data.py --full     # downloads public sources (~700 MB, mostly the 622 MB BMC book)
python analysis/fetch_rain_daily.py      # optional: IMD daily grids 1971-2025 (~1.4 GB); the extracted series is committed
python analysis/run_pipeline.py          # transcription checks -> ... -> app/public/data/*.json
python -m pytest -q                      # 31 tests

# 2. Web app
cd app
npm ci
npm test                                 # 41 tests
npm run build
npm run preview                          # http://localhost:4173
```

> **Windows PowerShell 5.1:** run each command on its own line as above. Its parser does not accept `&&`; use `;` to chain commands on one line instead.

The built app (`app/dist/`) is static, so it can be hosted on any free static host (GitHub Pages, Netlify, Cloudflare Pages). There are **no API keys and no paid services.** The only live calls are the free Open-Meteo forecast and the OpenFreeMap basemap, and the app shows clear states if either is unavailable.

## Repository layout
```
analysis/            reproducible pipeline (run_pipeline.py runs every step in order)
data/transcribed/    hand transcriptions of the official lists + review files
data/processed/      all outputs, incl. geocode/elevation caches and logs
data/raw/manifest.json  source URLs, access times, SHA-256 (raw files are re-downloaded, not committed)
notebooks/           01_findings.ipynb (reads data/processed/ only) + the script that builds it
docs/                data audit, data statement, methodology, evaluation, limitations, demo script, figures
app/                 React + TypeScript + MapLibre web app (Vite)
tests/               pytest suite
```

## Results of the checks (23 Oct 2026)
* `python analysis/run_pipeline.py`: completes (exit 0)
* `python -m pytest -q`: **31 passed**
* `npm test`: **41 passed**; `npm run lint`: clean; `npm run build`: success
* `python notebooks/make_findings_notebook.py`: executes all cells without errors (`notebooks/01_findings.ipynb`)
* Visual checks at 390 / 768 / 1440 px in light and dark themes (22 Oct, before the Plan and outlook additions)

## Attribution and responsible use
Data: India Meteorological Department (0.25° daily gridded rainfall, Pai et al. 2014); Brihanmumbai Municipal Corporation, BEST Undertaking and Mumbai Traffic Police (2026 publications, derived facts only); IMD via OpenCity; ERA5 and Copernicus GLO-90 via Open-Meteo (CC BY 4.0); Census 2011 via OpenCity; ward boundaries © DataMeet (CC BY-SA 2.5 IN); © OpenStreetMap contributors (ODbL); basemap © OpenMapTiles / OpenFreeMap.

The three-cause diagnosis idea (drainage capacity, list coverage, exposure) is adapted from JunkSnap's city / citizen / bin-access framing; no JunkSnap code is used.

RainGuard is a student prototype, **not an official BMC service or emergency warning system**, and it never claims a road is safe. For emergencies call the BMC helpline **1916**; for alerts see [dm.mcgm.gov.in](https://dm.mcgm.gov.in/) and [IMD](https://mausam.imd.gov.in/).

AI coding assistance was used during development; all data, findings and metrics come from executed code in this repository.
