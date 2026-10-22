# Five-minute video script: CityPulse RainGuard

**Before recording:** open the deployed app (or `cd app && npm run preview`) in a desktop browser window at about 1280 px wide, in light mode, on the **Map** tab. Close the place panel. Have the phone view ready (browser dev tools, or a phone). Speak at a steady pace: the narration is about 670 words, which fits five minutes with pauses for clicks.

Each block gives the time, **what to show**, and the words to say.

---

### 0:00–0:25 · Hook and user
**Show:** the Map tab, full screen. Slowly move the mouse over the orange dots.

> "Mumbai has three official lists of places that waterlog in the monsoon: from BMC, from BEST, and from the Mumbai Traffic Police. Together they name 251 places. Only 16 appear on more than one list.
> So if you are a BMC ward engineer with a few inspection teams, where do you start? What should each team check? And is tomorrow likely to be a heavy-rain day? That is the decision RainGuard supports."

### 0:25–1:05 · Data, and what it cannot do
**Show:** click the **Method** tab. Scroll to **Feasibility decision**, then slowly down the **Sources** table.

> "We started by checking what free public data actually exists. The lists name places, but give no dates. BMC's incident data is only a ward-level map. And no free source records when and where waterlogging happened.
> So RainGuard does not pretend to forecast flooding on a street. There is nothing to test that against, and we say so.
> What we can test is the trigger: heavy rain. We use 55 years of IMD daily rainfall, and every source here is free, with its licence and access date, and no API keys."

### 1:05–1:50 · Findings
**Show:** click **Insights**. Pause on **F2** (the bar chart of list combinations), then scroll to **F1**, then **F6**.

> "Three findings shape the product.
> First, the lists disagree. BMC's 2026 list says wards A, B and G North have no waterlogging spots. BEST lists 16 places there.
> Second, recorded incidents by ward mostly follow population. Population alone predicts a ward's incident class better than any model we tried, so we show that history as context, not as a hazard map.
> Third, heavy rain clusters. After a heavy-rain day, the next day is heavy 43 percent of the time, against 6 percent otherwise."

### 1:50–2:30 · Prediction and how we tested it
**Show:** click **Method**, scroll to **Evaluation: heavy-rain outlook**. Point at the test table, then the **Track record** table.

> "Here is the prediction. Every morning at 8:30, using the rain just measured, it gives the chance that the next 24 hours are a heavy-rain day.
> We trained it on 1971 to 2008, chose the model on 2009 to 2016, and tested it once on 2017 to 2025. It beats both baselines, the usual rate for the month and simple persistence, with a Brier skill of 0.22 and an AUC of 0.85.
> We also checked the live weather forecast. When it said heavy rain, it caught only 5 of 33 heavy days in 2024 and 2025. So the app never repeats its label. It shows how often each forecast amount actually came true."

### 2:30–3:35 · Live demo: the weekly plan
**Show:** click the **Plan** tab. Point at the first rows of **This week's plan**, then at the **What to check** column, then the **Plan stability** column.

> "This is the officer's screen. Twenty places this week, at most three from any one ward, so the teams cover 12 wards instead of 5.
> Each row says what to check. Kurla Depot Junction: no pump recorded. Confirm whether one is assigned before the monsoon."

**Show:** drag **Places your teams can inspect** down to **10**. Then click **Adjust ward history for population**, and watch the rows change.

> "Fewer teams? Drag the slider. Prefer to discount wards that report a lot simply because many people live there? One click.
> The order changes, and we show by how much. Worli Naka is on all three lists, but it stays in the plan in only 35 percent of weightings. The labels, though, come straight from the official lists, so the action does not depend on the weights."

**Show:** click **Back to the default plan**, then **Download plan**.

> "And the plan downloads as a spreadsheet the ward office can use."

### 3:35–4:20 · One place, end to end
**Show:** click **Map**. Type **Hindmata** in the search box and open **Hindmata Cinema**. Scroll slowly down the panel, pausing on each block heading.

> "Now one place. Hindmata Cinema in ward F South.
> What should a team check: it is named by BEST and the Traffic Police, but missing from BMC's own list. So: ask the ward to confirm it and add it.
> Every block carries a label: historical, estimated, forecast or unknown. The traffic diversion plan is here. The pump information is marked unknown, because it is not on BMC's list.
> And for residents: practical advice, the BMC helpline 1916, and a clear note that a road not on these lists is not guaranteed to be safe."

**Show:** close the panel, switch to the phone layout for two seconds, then toggle dark mode.

> "It works on a phone, and in dark mode."

### 4:20–5:00 · Limits and close
**Show:** click **Method**, scroll to **Limitations**. End on the Map tab.

> "What could make us wrong? The lists are undated and incomplete. 144 places are only known to the neighbourhood. The outlook predicts rain, not water on the road, and only city-wide. We looked for tide records and official disruption dates, and found none we could use.
> With BMC's dated complaint records and open rain-gauge data, this could become a real street-level early warning. Until then, RainGuard gives ward teams a ranked, explained plan, and tells them exactly how sure it is. Thank you."

---

## Likely judge questions

1. **Sources and terms?** BMC FPG 2026 and BEST booklets are publisher copyright, so we don't redistribute the PDFs; we use derived facts with attribution, and `fetch_data.py` re-downloads them. DataMeet wards are CC BY-SA 2.5 IN. ERA5, DEM and forecast via Open-Meteo are CC BY 4.0 (non-commercial). OSM is ODbL. IMD and Census via OpenCity are listed as public domain.
2. **How do you know these are real waterlogging places?** They are official 2026 government publications (BMC, BEST, Traffic Police). Every row is traceable to PDF and page, and verified against OCR or text. They are *expected* waterlogging locations, not dated incidents, and we say so.
3. **Three strongest findings?** (F2) 251 places, only 16 on 2+ lists; 2026 publications. (F1) Incident class tracks population, ρ = 0.835 across 24 wards (2016–2023/25). (F3) ERA5 recorded 69.6 mm against 944 mm on 26 July 2005, and is 20% drier than IMD over 1991–2021 (372 months).
4. **Baseline, and why this method?** Median and population baselines for the ward analysis. A rule-based score for prioritisation, because there are no labels to train or validate a model, and a transparent rule is what a planner can audit and adjust.
5. **Leakage?** The ward model uses only static covariates (population, area, terrain, listings). Cross-validation is leave-one-ward-out, and standardisation is fitted inside each fold. The heavy-rain outlook uses only rain measured up to 08:30 IST on the day it is issued (IMD's day ends at 08:30, confirmed with the 26 July 2005 storm), and its split is chronological. Test years were used once, after the model was chosen on validation years; a test checks that features never use future rain.
6. **What do the metrics mean?** MAE is in incident classes (1 class ≈ one legend bin). The permutation p is the share of 1,000 shuffled-target runs that did as well. Score robustness uses Spearman and top-20 Jaccard under random weights.
7. **Missing or biased incident data?** Incidents are complaints and follow population, so we show them as context, not hazard. Missing pumps and terrain stay missing; nothing is imputed.
8. **How do you explain a place's score?** The panel shows each component's value, the weights, the rank range and top-20 frequency, and the labels with their rules. The Plan sliders show how it changes.
13. **Is this a prediction or just a dashboard?** Both, at the levels the data allows. Places are prioritised by transparent rules, because there are no place-level outcomes. The city-wide heavy-rain outlook is a real prediction, tested on 2017–2025. We say plainly that it predicts rain, not waterlogging.
9. **Does the app say a road is safe?** No. It says the opposite in three places.
10. **Main limitations / what data would help?** See `docs/limitations.md`: dated geolocated complaints, open rain-gauge and tide data, a LiDAR DTM, and one versioned official list.
11. **Reproducible?** Yes: `pip install -r requirements.txt`, `python analysis/fetch_data.py --full`, `python analysis/run_pipeline.py`, `cd app && npm ci && npm run build`. Geocodes and elevations are cached in the repo, so results are identical offline.
12. **What runs free?** Everything. No API keys, no paid services. The forecast and basemap are free public services, and the app degrades gracefully without them.
