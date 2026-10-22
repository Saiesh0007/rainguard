# CityPulse RainGuard
## HackAMatch 1.0 — Project Specification

**Project theme:** CityPulse — Predict. Explain. Act.  
**Chosen urban problem:** Rainfall-related waterlogging in Mumbai, Maharashtra, India.  
**Primary users:** Mumbai residents and commuters.  
**Secondary users:** Civic teams and field-inspection planners.  
**Product format:** Free-to-deploy, mobile-first, responsive web application.  
**Data principle:** No fabricated observations, incidents, forecasts, metrics, citations, or claims.

> **Important implementation rule:** The proposed product must be grounded in verified public data. Do not claim that a location-level waterlogging prediction is accurate unless the available data and evaluation support that claim. If the data does not support forecasting, deliver transparent historical hotspot analysis and evidence-based risk prioritization instead.

---

## 0. Implementation status (22 October 2026)

The working implementation is in this repository. Where it differs from the plan below, **this section and the docs take precedence**.

| Plan item | What was actually built |
|---|---|
| §5 Feasibility audit | Done: [`docs/data_audit.md`](docs/data_audit.md). **Decision: risk prioritisation feasible, forecasting not feasible.** No free public source has dated, located waterlogging events. BMC's 120-gauge rainfall API requires authentication (not used). ERA5 covers Mumbai with one 25 km cell. |
| Historical incidents | No event-level data exists. We use **three official 2026 listings** (BMC FPG 2026 ward directory, 97 rows; BEST Annex IX, 84 rows; Mumbai Traffic Police diversion table, 90 location rows), merged into **251 distinct places**, plus BMC's **ward-level incident map** (digitised into 7 ordinal classes). |
| Rainfall | IMD gridded monthly (1901–2021, observed) and ERA5 daily (1991–2025, estimated) for context and a reliability check. A live Open-Meteo 3-day forecast is shown as **third-party**. |
| Geographic context | DataMeet BMC ward boundaries (CC BY-SA 2.5 IN); Copernicus GLO-90 DEM; OSM Nominatim geocoding (one cached batch); OpenFreeMap basemap. |
| §6 EDA | Five computed findings (F1–F5) in `data/processed/eda_findings.json`, the Insights screen and `docs/figures/`. |
| §6 Baseline / model | Ward level: median and population baselines vs terrain/listing models, leave-one-ward-out CV with permutation tests (population baseline wins). Location level: within-ward terrain case-control (not significant). Prioritisation: rule-based score with sensitivity and ablation; **no predictive metric is claimed**. |
| §8 P0 features | All built: responsive map with legend and list alternative, evidence panel with five evidence labels, charts, citizen guidance, methodology page, reproducible pipeline. Loading, empty, error, stale-forecast and offline-basemap states are implemented and tested. |
| §8 P1 features | Civic prioritisation view with adjustable weights, ward/attribute filters, place search and CSV download. Route context was **not** built (no reliable free data). |
| §10 Stack | Python pipeline (pandas, NumPy, SciPy, Shapely, PyMuPDF, Matplotlib); React + TypeScript + Vite + MapLibre GL; static JSON instead of an API. scikit-learn was not needed. |
| §11 Structure | As planned, except: no notebook (the report is `docs/` plus the Insights screen); added `data/transcribed/` for hand transcriptions and review files. |
| §12 Quality bar | pytest 21 passed; Vitest 35 passed; ESLint clean; production build succeeds; visual checks at 390/768/1440 px in light/dark. See [`docs/evaluation.md`](docs/evaluation.md). |

Documentation: [`README.md`](README.md), [`docs/methodology.md`](docs/methodology.md), [`docs/evaluation.md`](docs/evaluation.md), [`docs/limitations.md`](docs/limitations.md), [`docs/data_statement.md`](docs/data_statement.md), [`docs/demo_script.md`](docs/demo_script.md) (includes judge Q&A).

---

## 1. Product vision

CityPulse RainGuard helps people understand where rainfall-related waterlogging has occurred, what current public data says about conditions, and which areas may warrant extra caution or inspection.

The product follows the CityPulse decision loop:

1. **Discover** — Find patterns and recurring waterlogging hotspots.
2. **Explain** — Show the evidence, data coverage, freshness, uncertainty, and limitations behind each assessment.
3. **Predict, if justified** — Estimate risk only when suitable data supports a defensible model and validation.
4. **Act** — Offer cautious, practical travel-awareness guidance for citizens and inspection-prioritization support for civic teams.

This is a decision-support prototype, not an official emergency service, guaranteed safe-route system, or replacement for civic authority advisories.

## 2. Problem statement

During Mumbai's monsoon, heavy rainfall can disrupt roads and local travel. Citizens may struggle to find consolidated, evidence-backed information about locations with a history of waterlogging. Civic teams may also benefit from a transparent way to review recurring hotspots and prioritize inspections.

RainGuard will investigate whether publicly available rainfall, historical waterlogging, and geographic data can be combined into a useful, explainable application.

The project must first verify the existence, accessibility, license/terms, time coverage, geographic coverage, and quality of each proposed data source. The application must clearly disclose gaps instead of filling them with invented values.

## 3. Goals and non-goals

### Goals

- Build a polished, mobile-first experience that works on phones, tablets, and desktops.
- Map verified historical waterlogging records and relevant rainfall/geographic data where available.
- Surface at least three genuine exploratory data analysis (EDA) findings.
- Explain each hotspot or risk assessment using visible evidence.
- Compare any proposed model with a simple baseline.
- Evaluate forecasts or classifications using a suitable validation method.
- Communicate data freshness, coverage, uncertainty, and known limitations.
- Provide useful, cautious actions for citizens and civic inspection planning.
- Make setup, data preparation, analysis, and evaluation reproducible.
- Use free public data and free-to-deploy services; no paid API or paid AI endpoint may be required for the core experience.

### Non-goals

- Do not claim complete coverage of Mumbai unless the data establishes it.
- Do not claim a road is safe merely because no incident appears in the dataset.
- Do not issue official emergency alerts or impersonate civic authorities.
- Do not guarantee a waterlogging forecast.
- Do not use private, scraped, or licensed data in violation of its terms.
- Do not fabricate historical incidents, rainfall measurements, labels, model scores, or demo outcomes.
- Do not make route-safety guarantees or claim real-time conditions without a verified live source.

## 4. Users and core journeys

### Citizen journey

1. Open the app and see a map and a concise status summary.
2. Choose a location or hotspot.
3. Inspect the evidence: historical reports, rainfall data, observation time, and data coverage.
4. Read a plain-language explanation of the assessment and its confidence/limitations.
5. Make an informed travel decision and consult official advisories when needed.

### Civic inspection journey

1. Open the hotspot overview.
2. Review recurring locations and the evidence supporting their prioritization.
3. Filter by time period or available risk/evidence categories.
4. Inspect a location's history, data quality, and rationale.
5. Use the output as an inspection-prioritization aid, not an automated order or official determination.

## 5. Required data feasibility audit — do this before building predictions

Create `docs/data_audit.md` before making strong product claims. For every source, record:

- Dataset/source name and publisher.
- Direct source URL and access date.
- License, terms of use, and attribution requirements.
- Geographic coverage and spatial resolution.
- Time range, update frequency, and freshness.
- Available fields and units.
- Whether it contains actual waterlogging incidents, rainfall observations, forecasts, or only geographic context.
- Missing values, duplicate records, inconsistent units, location precision, and likely reporting bias.
- How the data can be downloaded or accessed reproducibly.
- Whether redistribution in the repository is permitted; if not, document retrieval instructions instead.

### Candidate data categories to investigate

These are research leads, not confirmation that a usable dataset exists. Verify each source before relying on it.

1. **Rainfall observations:** official public meteorological or government sources with station-level or gridded rainfall observations and clear timestamps.
2. **Historical waterlogging incidents:** official municipal open-data portals, published reports, public incident datasets, or other lawful public records with location and date/time.
3. **Geographic context:** public road networks, ward boundaries, elevation/drainage-related layers, or other suitable open geospatial datasets with clear terms.
4. **Weather forecasts:** only if a suitable free public source provides terms and update information compatible with the project.

Do not treat social posts, search snippets, map labels, or anecdotal reports as verified incident ground truth without an explicit collection and validation methodology.

### Data feasibility decision

After auditing sources, write a short decision:

- **Forecasting feasible:** the dataset has enough temporally aligned observations and reliable target labels to support honest chronological or otherwise appropriate evaluation.
- **Risk prioritization feasible, forecasting not feasible:** historical hotspots and contextual signals are useful, but there are not enough labels or observations to validate forecasts.
- **Insufficient evidence:** build a data-exploration prototype, clearly show the missing data, and avoid unsupported risk claims.

Proceed with the simplest defensible option.

## 6. Analysis and methodology

### Data preparation

Build a repeatable pipeline that:

- Loads source data from documented files or source URLs.
- Validates required columns, types, units, timestamps, coordinates, and coordinate reference systems.
- Removes or flags duplicates using documented rules.
- Handles missing values transparently; do not silently impute target labels.
- Normalizes timestamps and units where justified.
- Maps observations to geographic areas only with a documented spatial method.
- Records excluded rows and reasons.
- Produces clean, versioned analysis outputs.
- Preserves source attribution and source-to-output traceability.

### Exploratory data analysis

Produce at least **three genuine findings** from the actual data. Possible questions, only if supported by available fields:

- Which locations or wards have the most recorded waterlogging incidents?
- How do recorded incidents vary by month, date, or time of day?
- Is there a measurable association between rainfall intensity/accumulation and recorded incidents?
- Which areas have sparse reporting or weak data coverage?
- How do hotspot patterns change across the available time period?

Every finding must include its calculation, time period, sample size where relevant, caveats, and a chart or map. Do not pre-write findings or make up numbers before running the analysis.

### Baseline and model selection

Start with a simple, transparent baseline. Choose a method only after inspecting the data and target:

- For forecasting incident counts or continuous outcomes, consider a suitable historical-average or seasonal baseline before more complex models.
- For classification, compare against a simple majority-class or other appropriate baseline and report class balance.
- For prioritization without reliable target labels, use a clearly described rule-based score based only on verified inputs. Label it a **prioritization score**, not a probability or validated forecast.
- Avoid complex models if the dataset is too small, biased, incomplete, or poorly aligned.

### Validation

- Keep training and evaluation data separate.
- For time-dependent data, prefer chronological splits or rolling-origin evaluation.
- Prevent future information from leaking into features.
- Choose metrics appropriate to the task and explain why.
- For regression/forecasting, report relevant metrics such as MAE or RMSE against the baseline.
- For classification, report suitable precision/recall and confusion-matrix information; do not rely on accuracy alone when classes are imbalanced.
- For prioritization without reliable labels, do not fabricate predictive metrics. Evaluate rule behavior and data sensitivity, and explain that predictive performance has not been established.
- Report sample sizes, class imbalance, missing labels, spatial/temporal coverage, and likely sampling/reporting bias.
- Include uncertainty or confidence language that is justified by the method and data.

All reported metrics must be generated from actual code execution. Never claim tests, evaluation, or model performance without running them.

## 7. Risk assessment and explanation design

Every location-level assessment must distinguish among:

- **Observed:** directly measured or recorded source data.
- **Historical:** an event or pattern recorded in the past.
- **Estimated:** output from a transparent analytical method.
- **Forecast:** a model's estimate of a future outcome, only if properly validated.
- **Unknown:** unavailable, stale, or insufficient evidence.

For each assessment, show as applicable:

- Location and geographic precision.
- Assessment category or score, with a definition.
- Evidence used and the time period covered.
- Rainfall measurement and timestamp, if available.
- Historical incident count or summary, if available.
- Data freshness and coverage.
- Key reasons the assessment was produced.
- Missing or conflicting evidence.
- Limitations and what would change the assessment.

Never convert a rule-based score into a percentage probability unless a defensible calibration method supports it.

## 8. Product features

### P0 — Required for the hackathon

1. **Responsive interactive map**
   - Display only locations/areas supported by the actual data.
   - Distinguish historical records from current observations and estimates.
   - Provide a legend, accessible controls, and a useful list alternative.
   - Include loading, empty, error, and no-coverage states.

2. **Hotspot explorer**
   - Select a hotspot or area to open its evidence panel.
   - Show verified historical records and relevant contextual data.
   - Support filters only where the underlying data supports them.

3. **Explainable assessment panel**
   - Show the factors used, source attribution, timestamp, coverage, and limitations.
   - Avoid opaque labels such as “high risk” without a documented rule or model behind them.

4. **Analysis charts**
   - Show genuine EDA outputs such as incident patterns over time, location comparisons, rainfall patterns, and data coverage.
   - All charts must be connected to real analysis outputs, not hardcoded demo numbers.

5. **Citizen guidance**
   - Give cautious, actionable language based on the evidence.
   - Link to verified official sources/advisories when available.
   - Do not guarantee route safety or invent current road closures.

6. **Data and methodology page**
   - Document sources, licenses/terms, data freshness, cleaning, methods, evaluation, limitations, and attribution.

7. **Reproducibility**
   - Include setup, data retrieval, preprocessing, analysis, test, and build instructions.
   - Keep secrets out of the repository.

### P1 — Build only after P0 works

- Civic inspection-prioritization view.
- Search by area/ward or supported location name.
- Time-period comparisons.
- Downloadable summary of analysis results.
- Optional route-context feature only if accurate, free, and supported by data; do not describe it as a safe-route guarantee.

## 9. UI/UX direction

### Design principles

- Mobile-first, responsive, fast, and readable in outdoor conditions.
- Modern civic-tech visual identity: calm, trustworthy, map-led, data-dense but not cluttered.
- Clear information hierarchy and accessible contrast.
- Use plain language rather than unexplained data-science terminology.
- Use colors alongside text/icons/patterns so risk is not communicated by color alone.
- Never use visual polish to imply greater certainty than the evidence warrants.

### Main screens

1. **Home / map**
   - CityPulse RainGuard brand.
   - Current data freshness and a short evidence-based summary.
   - Interactive map with legend.
   - Search/filter controls when supported.
   - List view for accessibility and small screens.

2. **Location detail**
   - Area/location name and coordinates or geographic boundary.
   - Assessment type: historical, estimated, or forecast.
   - Evidence and source timestamps.
   - Relevant charts and historical records.
   - Explanation, uncertainty, missing data, and recommended next step.

3. **Insights**
   - At least three genuine EDA findings.
   - Charts with labels, units, sample/time coverage, and source notes.

4. **Methodology & data**
   - Dataset register, cleaning, model/baseline, validation, caveats, and known gaps.

5. **Civic prioritization** (if time allows)
   - Transparent, sortable list of locations for possible inspection.
   - Display the reason and evidence for each priority.
   - Clearly state that this is decision support, not an official directive.

### UI states

Implement loading, empty, error, stale-data, partial-coverage, and unsupported-location states. Do not replace failed data with fabricated examples. If a visual placeholder is used during development, label it conspicuously as a placeholder and remove it from the real-data demo.

## 10. Suggested technical architecture

Choose tools based on the existing repository and team capability. Keep the architecture simple and free to run.

One possible implementation:

- **Frontend:** React with TypeScript and a responsive styling system.
- **Map:** a library and tile/source provider whose usage terms are verified; no paid key required for core use.
- **Charts:** a lightweight charting library.
- **Analysis:** Python with pandas, GeoPandas where needed, and scikit-learn or statsmodels only if appropriate.
- **API/backend:** a lightweight Python API or static generated analysis outputs, depending on deployment constraints.
- **Storage:** versioned local data/artifacts or a free-tier option that is not essential to core functionality.
- **Tests:** unit tests for data transformations and core logic, plus UI/build checks.

This is a suggestion, not a mandatory stack. Inspect the current repository before choosing or replacing frameworks. Do not introduce unnecessary infrastructure.

## 11. Suggested repository structure

```text
citypulse-rainguard/
├── README.md
├── Project.md
├── docs/
│   ├── data_audit.md
│   ├── data_statement.md
│   ├── methodology.md
│   ├── evaluation.md
│   ├── limitations.md
│   └── demo_script.md
├── data/
│   ├── README.md
│   ├── raw/              # only if redistribution terms allow
│   └── processed/
├── notebooks/
│   └── exploratory_analysis.ipynb
├── analysis/
│   ├── fetch_data.py
│   ├── clean_data.py
│   ├── eda.py
│   ├── baseline.py
│   └── evaluate.py
├── app/
│   └── ...               # adapt to the selected frontend/backend
├── tests/
└── requirements.txt      # or the package manager's lock/config files
```

Adapt this to the repository. Do not create empty files just to match the tree.

## 12. Testing and quality bar

Before declaring the project complete:

- Run the documented data pipeline from a clean state where feasible.
- Check schema, duplicates, missing values, timestamp validity, units, and coordinate ranges.
- Verify that charts and map features use the actual processed outputs.
- Verify that the assessment explanation matches the implemented calculation.
- Verify that forecast outputs are not shown if forecasting is unsupported.
- Run tests, lint, and production build where supported; record actual outcomes.
- Test the main citizen journey on mobile, tablet, and desktop widths.
- Test loading, empty, error, stale-data, and partial-coverage states.
- Check keyboard accessibility, readable labels, and map/list alternatives.
- Confirm no API secrets or credentials are committed.
- Confirm all source URLs, terms, and attribution notes are present.
- Remove or visibly label any placeholder content.
- Do not claim a test passed unless it was executed.

## 13. Hackathon submission mapping

The official challenge asks for a focused urban problem, public-data preparation, at least three EDA findings, an appropriate method/baseline, evaluation/validation, and a decision interface that communicates location/time/signal/evidence/estimate when appropriate/action. RainGuard should map each item to a concrete artifact.

| Challenge requirement | RainGuard evidence |
|---|---|
| Clear problem framing | `Project.md` and README |
| Public data and preparation | `docs/data_audit.md`, `docs/data_statement.md`, repeatable pipeline |
| At least 3 EDA findings | Notebook, charts, and Insights screen |
| Appropriate method and baseline | `docs/methodology.md`, code |
| Evaluation and validation | `docs/evaluation.md`, executed metrics or explicit explanation why predictive metrics are not valid |
| Decision interface | Map, location detail, evidence, estimate only if justified, and action |
| Explainability and uncertainty | Assessment rationale, freshness, coverage, limitations |
| Reproducibility | Exact setup/run/test commands |
| Presentation | Five-minute demo script and limitations |

## 14. Five-minute demo plan

- **0:00–0:30 — Problem:** Explain the Mumbai waterlogging decision problem and target users.
- **0:30–1:15 — Data:** Show verified public sources, coverage, and preparation.
- **1:15–2:00 — Findings and method:** Present three genuine EDA findings, baseline, and evaluation approach.
- **2:00–4:30 — Live demo:** Explore the map, select a location, inspect evidence and explanation, and show citizen/civic action.
- **4:30–5:00 — Limitations and next steps:** Explain uncertainty, missing data, coverage gaps, and what further data would improve the system.

## 15. Likely judge questions

Prepare concise, honest answers to:

1. Which data sources did you use, and what are their terms?
2. How do you know these are real waterlogging incidents?
3. What are your three strongest findings, and what sample/time period supports each?
4. What is the baseline, and why is the chosen method appropriate?
5. How did you prevent data leakage?
6. How did you validate the model, and what do the metrics mean?
7. What happens when incident data is missing or biased?
8. How do you explain a location's risk assessment?
9. Does the application claim a road is safe? (It must not.)
10. What are the main limitations, and what additional data would help?
11. Can another team member reproduce the results from the README?
12. What runs for free, and which third-party terms apply?

## 16. Instructions for the coding agent

You are implementing CityPulse RainGuard for HackAMatch 1.0. Build the working project, not just a plan.

1. Read the official HackAMatch problem statement and this `Project.md` completely.
2. Inspect the existing repository and preserve useful work.
3. Start with the data feasibility audit. Verify source URLs, terms, coverage, fields, and reproducible access. Do not assume candidate sources exist or are suitable.
4. If the proposed data cannot support prediction, do not fake it. Pivot to historical hotspot analysis or transparent prioritization and explain the limitation.
5. Implement a reproducible data pipeline and perform real EDA. Produce at least three genuine findings.
6. Implement a simple baseline before trying a more complex method. Validate appropriately and report only metrics actually computed.
7. Build the responsive application and connect the interface to actual processed data/analysis outputs.
8. Clearly distinguish observed, historical, estimated, forecast, and unknown information.
9. Use free tools/services for the core project. Verify third-party data and map terms.
10. Run the available tests, lint, and production build; fix issues and record results honestly.
11. Update `README.md` and all documentation to match the actual implementation, not this plan if implementation differs.
12. Prepare a five-minute demo script and likely judge Q&A.
13. Do not stop after giving a plan. Continue through implementation and testing. If blocked, state the exact blocker and implement the best defensible alternative.
14. Prioritize evidence, reproducibility, and correctness over unnecessary complexity or decorative effects.

## 17. Definition of done

The project is ready for submission when:

- The core application runs using documented instructions.
- Its central map and evidence panel are connected to verified data.
- The data audit and licensing/attribution notes are complete.
- At least three genuine EDA findings are reproducible.
- The method is compared with a baseline where applicable.
- Evaluation is honest and appropriate, or the absence of valid predictive evaluation is clearly explained.
- Risk assessments explain their evidence and limitations.
- The UI works responsively and includes empty/error/stale-data states.
- Tests/build results are documented truthfully.
- README, Project.md, methodology, evaluation, limitations, and demo script match the actual implementation.
- No fabricated data or unsupported prediction/safety claims remain.
