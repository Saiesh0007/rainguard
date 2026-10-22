# Five-minute demo script: CityPulse RainGuard

**Setup before you present:** run `cd app && npm run preview` (or open the deployed URL). Keep these tabs open: Map, Insights, Civic, Method. Have backup screenshots ready in case the basemap or forecast is offline. The app still works without them, because the list view and all evidence are local.

---

### 0:00–0:30 · Problem and user
> "Every monsoon, Mumbai's roads waterlog. Citizens hear 'avoid flood-prone areas', but which areas, according to whom, and how sure are we? Civic teams need to decide where to inspect before the rains. RainGuard brings the official evidence together and is honest about what it doesn't know."

Users: commuters and residents, and BMC ward inspection planners.

### 0:30–1:15 · Data and its quality
> "We first checked what free public data actually exists. There is **no public dataset of dated, located waterlogging events**. So we don't forecast: there's nothing to validate a forecast against."

Show **Method → Sources**. Key points:
* We found **three official 2026 lists**: BMC's Flood Preparedness Guidelines, BEST's flood-prone list, and the Mumbai Traffic Police diversion plan. We transcribed all 273 rows and verified them against the PDFs by OCR and text matching (no phone numbers; residents' names redacted).
* We digitised BMC's ward incident map. Rainfall comes from IMD (1901–2021) and ERA5. Terrain comes from the Copernicus DEM.
* **Strongest insight (Insights F2):** "These three lists name **251 distinct places, but only 16 appear on more than one list**. BMC says wards A, B and G/N have no waterlogging spots; BEST lists 16 there."

### 1:15–2:00 · Method, baseline, validation
Show **Insights F1, F3, F4** and **Method → Evaluation**:
* "Which wards record the most incidents? A **population-only baseline** predicts the ward incident class with an error of 0.73 classes, against 1.92 for the median baseline. Adding terrain doesn't help. **Recorded incidents mostly follow where people live.**"
* "Is terrain a signal at street level? Listed places are slightly lower than their ward, but **not significantly** (p = 0.17), so terrain is off in our score by default."
* "Global-model rainfall recorded **70 mm for 26 July 2005**, a day with **944 mm** at Santacruz. That's why we label the live forecast as third-party and never call it ours."
* Prioritisation: "A transparent, rule-based score: ward history, how many official lists agree, and nearby listings. We tested it with 2,000 random weightings, and we show how unstable the top of the list is."

### 2:00–4:30 · Live demo: signal → explanation → action
1. **Map (citizen).** "Orange dots are listed places; hollow rings mean we only know the neighbourhood. Ward shading is incident history." Point out the 3-day **Rain outlook** card with its *Forecast* label.
2. Search **"Hindmata"** and open it. Walk down the panel:
   * *Historical:* named by BEST and the Traffic Police (not by BMC's 2026 list), with the **traffic diversion plan**.
   * *Historical, ward-level:* F/S is class 4 of 7.
   * *Forecast:* the city outlook. *Estimated:* exact map position; terrain marked unvalidated.
   * *Unknown:* pump data, because it's not on BMC's list.
   * **What you can do:** don't wade; leptospirosis advice from BMC; helpline 1916; "not being listed doesn't mean safe".
3. Open **Worli Naka**, the only place on all three lists.
4. Switch to **List** view to show the keyboard-accessible alternative. Search something unlisted to show the honest empty state.
5. **Civic tab.** "Planners see a transparent ordering." Drag *Ward incident history* to 0 and watch the order change. Tick **"BMC spots with no pump listed"**: 43 of 97 BMC spots have no pump recorded. **Download CSV**. Point to the "decision support, not an official directive" line and the top-20 stability column.
6. Toggle **dark mode** and show the phone layout (resize or use a phone).

### 4:30–5:00 · Limitations and next steps
> "What could make us wrong: the lists are undated and inconsistent, 144 places are only located to the neighbourhood, and free rainfall can't see neighbourhoods. With BMC's dated complaint records and open rain-gauge and tide feeds, this becomes a validated, location-level early-warning model. Until then, RainGuard shows the evidence and its gaps honestly."

---

## Likely judge questions

1. **Sources and terms?** BMC FPG 2026 and BEST booklets are publisher copyright, so we don't redistribute the PDFs; we use derived facts with attribution, and `fetch_data.py` re-downloads them. DataMeet wards are CC BY-SA 2.5 IN. ERA5, DEM and forecast via Open-Meteo are CC BY 4.0 (non-commercial). OSM is ODbL. IMD and Census via OpenCity are listed as public domain.
2. **How do you know these are real waterlogging places?** They are official 2026 government publications (BMC, BEST, Traffic Police). Every row is traceable to PDF and page, and verified against OCR or text. They are *expected* waterlogging locations, not dated incidents, and we say so.
3. **Three strongest findings?** (F2) 251 places, only 16 on 2+ lists; 2026 publications. (F1) Incident class tracks population, ρ = 0.835 across 24 wards (2016–2023/25). (F3) ERA5 recorded 69.6 mm against 944 mm on 26 July 2005, and is 20% drier than IMD over 1991–2021 (372 months).
4. **Baseline, and why this method?** Median and population baselines for the ward analysis. A rule-based score for prioritisation, because there are no labels to train or validate a model, and a transparent rule is what a planner can audit and adjust.
5. **Leakage?** The ward model uses only static covariates (population, area, terrain, listings). Cross-validation is leave-one-ward-out, and standardisation is fitted inside each fold. No forecast is made, so there is no future information to leak.
6. **What do the metrics mean?** MAE is in incident classes (1 class ≈ one legend bin). The permutation p is the share of 1,000 shuffled-target runs that did as well. Score robustness uses Spearman and top-20 Jaccard under random weights.
7. **Missing or biased incident data?** Incidents are complaints and follow population, so we show them as context, not hazard. Missing pumps and terrain stay missing; nothing is imputed.
8. **How do you explain a place's score?** The panel shows each component's value, the weights, the rank range and top-20 frequency. The Civic sliders show how it changes.
9. **Does the app say a road is safe?** No. It says the opposite in three places.
10. **Main limitations / what data would help?** See `docs/limitations.md`: dated geolocated complaints, open rain-gauge and tide data, a LiDAR DTM, and one versioned official list.
11. **Reproducible?** Yes: `pip install -r requirements.txt`, `python analysis/fetch_data.py --full`, `python analysis/run_pipeline.py`, `cd app && npm ci && npm run build`. Geocodes and elevations are cached in the repo, so results are identical offline.
12. **What runs free?** Everything. No API keys, no paid services. The forecast and basemap are free public services, and the app degrades gracefully without them.
