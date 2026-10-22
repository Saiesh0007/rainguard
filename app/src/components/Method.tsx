import type { RainGuardData } from "../types";
import EvidenceChip from "./EvidenceChip";
import { EVIDENCE, type EvidenceKind } from "../lib/labels";

const OUTLOOK_LABEL: Record<string, string> = {
  B0_climatology: "Baseline: usual share for the month",
  B1_persistence: "Baseline: was today heavy?",
  M1_logistic: "Logistic: today's rain",
  M2_logistic: "Logistic: today's rain + last 3 days + month",
};

const MODEL_LABEL: Record<string, string> = {
  B0_median: "Baseline: predict the median class",
  B1_population: "Baseline: population only",
  B2_population_area: "Population + ward area",
  M1_plus_terrain: "+ terrain (median elevation, low-lying share)",
  M2_plus_listed_spots: "+ number of BMC-listed spots",
};

export default function Method({ data }: { data: RainGuardData }) {
  const ev = data.evaluation.ward_level;
  const v = data.verification as unknown as Record<string, Record<string, unknown>>;
  const c = data.cleaning;
  const o = data.outlook.observed_model;
  const fc = data.outlook.forecast_track_record;
  const fcf = fc.forecast_ge_64_5mm;
  const pct = (x: number | null) => (x === null ? "—" : `${Math.round(x * 100)}%`);
  return (
    <div className="page prose">
      <header className="page__head">
        <h2>Methodology &amp; data</h2>
        <p className="lead">How every number in RainGuard was produced, what it can and cannot tell you, and where it came from.</p>
      </header>

      <section className="card">
        <h3>Feasibility decision</h3>
        <p>
          <strong>Risk prioritisation is feasible; location-level forecasting is not.</strong> No public dataset gives dated,
          located waterlogging events for Mumbai. Officially published lists name places that waterlog, but without dates;
          BMC's incident data is only published as a ward-level map; and free rainfall data is either monthly (IMD) or a
          ~25 km model grid (ERA5) that cannot resolve neighbourhoods. With no event labels there is nothing to validate a
          forecast against, so RainGuard does not make one.
        </p>
        <p>
          <strong>What it does predict:</strong> whether tomorrow will be a heavy-rain day for the city as a whole (IMD ≥ {data.outlook.heavy_mm} mm),
          the trigger BMC prepares pumps and teams for. That target has 50+ years of observed daily data, so it can be tested on years the
          model never saw. It is a rain outlook, not a waterlogging forecast, and it is the same for every place.
        </p>
      </section>

      <section className="card">
        <h3>Five kinds of information</h3>
        <ul className="legend-list">
          {(Object.keys(EVIDENCE) as EvidenceKind[]).map((k) => (
            <li key={k}><EvidenceChip kind={k} /> {EVIDENCE[k].help}</li>
          ))}
        </ul>
      </section>

      <section className="card">
        <h3>Sources</h3>
        <div className="table-scroll">
          <table className="data-table data-table--cards">
            <thead><tr><th scope="col">Source</th><th scope="col">Kind</th><th scope="col">Used for</th><th scope="col">Terms</th><th scope="col">Accessed (UTC)</th></tr></thead>
            <tbody>
              {data.sources.map((s) => (
                <tr key={s.id}>
                  <td data-label="Source" className="cell-place"><a href={s.url} target="_blank" rel="noreferrer">{s.name}</a><span className="fine block">{s.publisher}</span></td>
                  <td data-label="Kind">{s.kind}</td><td data-label="Used for">{s.use}</td><td data-label="Terms">{s.terms}</td>
                  <td data-label="Accessed">{s.accessed ? s.accessed.slice(0, 10) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card">
        <h3>Preparing the data</h3>
        <ol>
          <li>Downloaded every source with a manifest of URL, time and SHA-256 hash.</li>
          <li>Transcribed the three official lists by hand from the PDFs (no phone numbers; residents' names redacted), then checked
            each row automatically against the PDF text or OCR: BMC {String(v.bmc_fpg2026.matched)}/{String(v.bmc_fpg2026.rows)},
            BEST {String(v.best_annex_ix_2026.matched)}/{String(v.best_annex_ix_2026.rows)},
            traffic police {String(v.mtp_diversions_2026.matched)}/{String(v.mtp_diversions_2026.rows)} matched; the rest were checked by eye.</li>
          <li>Digitised BMC's ward incident map by matching colours to its legend (3 sample points per ward, all unanimous).</li>
          <li>Geocoded names with OpenStreetMap Nominatim, rejected results outside the stated ward, and manually downgraded false
            matches (never moved a point). Result: {c.by_precision.point ?? 0} exact, {c.by_precision.street ?? 0} road-level,
            {" "}{c.by_precision.area ?? 0} neighbourhood-level and {c.by_precision.not_mappable ?? 0} unmappable places.</li>
          <li>Merged duplicates within a list and matches across lists in the same ward → {c.unique_locations} distinct places.</li>
        </ol>
      </section>

      <section className="card">
        <h3>Evaluation: what explains ward incident history?</h3>
        <p>Leave-one-ward-out cross-validation over {ev.n_wards} wards, predicting the incident class (1–7). Lower error is better.</p>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Model</th><th scope="col">Mean abs. error (classes)</th><th scope="col">Spearman ρ</th><th scope="col">Permutation p</th></tr></thead>
            <tbody>
              {Object.entries(ev.models).map(([k, m]) => (
                <tr key={k}>
                  <td>{MODEL_LABEL[k] ?? k}</td>
                  <td>{m.loo_mae_classes.toFixed(2)}</td>
                  <td>{m.loo_spearman === null ? "—" : m.loo_spearman.toFixed(2)}</td>
                  <td>{m.permutation_p_value ?? "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          Population alone cuts the error from {ev.models.B0_median.loo_mae_classes.toFixed(2)} to{" "}
          {ev.models.B1_population.loo_mae_classes.toFixed(2)} classes. Terrain and listed-spot counts add nothing reliable.
          So recorded incidents largely follow where people live (and report) — which is why the app shows incident history as
          context, not as a hazard map.
        </p>
      </section>

      <section className="card">
        <h3>Evaluation: heavy-rain outlook (chronological test)</h3>
        <p>
          Target: {o.target.toLowerCase()}, {o.season}. Trained on {o.split_years.train[0]}–{o.split_years.train[1]}, model chosen on{" "}
          {o.split_years.validate[0]}–{o.split_years.validate[1]}, then refitted and tested once on {o.split_years.test[0]}–{o.split_years.test[1]}{" "}
          ({o.n_days.test.toLocaleString()} days, {pct(o.heavy_share.test)} heavy). Lower Brier score is better; skill above 0 beats the monthly baseline.
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Model (test years)</th><th scope="col">Brier score</th><th scope="col">Skill vs monthly baseline (95% interval)</th><th scope="col">ROC AUC</th></tr></thead>
            <tbody>
              {Object.entries(o.test).map(([k, m]) => (
                <tr key={k}>
                  <td>{OUTLOOK_LABEL[k] ?? k}{k === o.chosen_on_validation ? " — chosen on validation" : ""}</td>
                  <td>{m.brier.toFixed(4)}</td>
                  <td>{m.brier_skill_vs_climatology.toFixed(3)}{m.brier_skill_95ci ? ` (${m.brier_skill_95ci[0]} to ${m.brier_skill_95ci[1]})` : ""}</td>
                  <td>{m.auc.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          Reliability of the chosen model on the test years (does a 30% outlook come true about 30% of the time?):
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Predicted chance</th><th scope="col">Days</th><th scope="col">Mean predicted</th><th scope="col">Observed heavy share</th></tr></thead>
            <tbody>
              {o.test_reliability_chosen.map((r) => (
                <tr key={r.bin}><td>{r.bin}</td><td>{r.n}</td><td>{pct(r.mean_predicted)}</td><td>{pct(r.observed_share)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <p>
          <strong>Track record of the live forecast</strong> ({fc.period}, {fc.n_days} days, {fc.observed_heavy_days} heavy): when the
          day-ahead forecast said {data.outlook.heavy_mm} mm or more, it caught {fcf.hits} of {fcf.hits + fcf.misses} heavy-rain days
          ({pct(fcf.probability_of_detection)}), and {pct(fcf.false_alarm_ratio)} of its heavy-rain calls were false alarms.
        </p>
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th scope="col">Day-ahead forecast</th><th scope="col">Days</th><th scope="col">Heavy-rain days that followed</th></tr></thead>
            <tbody>
              {fc.by_forecast_amount.map((r) => (
                <tr key={r.forecast}><td>{r.forecast}</td><td>{r.n_days}</td><td>{r.heavy_days} ({pct(r.heavy_share)})</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="fine">{fc.caveat}</p>
      </section>

      <section className="card">
        <h3>The inspection-priority score</h3>
        <p>
          A rule-based weighted average of: ward incident history, how many official lists name the place, and how many other
          listed places are within 1 km. A terrain factor exists but is off by default because it showed no significant signal.
          Missing factors are skipped, never filled in. Sensitivity was tested with {data.sensitivity.n_weight_draws.toLocaleString()} random weightings
          and by dropping each factor:
        </p>
        <ul>
          {Object.entries(data.sensitivity.ablation_drop_one_component).map(([k, a]) => (
            <li key={k}>Without <em>{k.replaceAll("_", " ")}</em>: ordering correlation {a.spearman_vs_default}, top-20 overlap {a.top20_jaccard}.</li>
          ))}
        </ul>
        <p>
          Because recorded ward incidents mostly follow population, an alternative factor uses only incidents <em>beyond</em> what population
          explains. It is off by default and one click away in the Plan tab; its ordering correlates {data.sensitivity.population_adjusted_alternative.spearman_vs_default} with
          the default.
        </p>
        <p>
          The weekly plan takes places in priority order with at most {data.allocation.cap_per_ward} per ward. Across the random weightings,
          the default {data.allocation.k}-place plan had a median overlap of {data.allocation.plan_jaccard_vs_default.median} with the re-weighted plan,
          so each place in the plan shows how often it stays in. Rule-based labels (no pump recorded, missing from BMC's list, traffic
          diversion, exact spot unknown) say what to check and do not depend on the weights.
        </p>
        <p>No accuracy or precision figure is reported for this score: there are no dated flood observations to test it against.</p>
      </section>

      <section className="card">
        <h3>Limitations</h3>
        <ul>
          <li>The lists say where authorities <em>expect</em> waterlogging; they are not dated observations, and they disagree with each other.</li>
          <li>Absence from every list does not mean a road is safe.</li>
          <li>{c.by_precision.area ?? 0} of {c.unique_locations} places could only be placed at neighbourhood level.</li>
          <li>The ward incident map is binned, its period is ambiguous (2016–2023 vs 2016–2025) and it counts complaints, which follow population.</li>
          <li>Rainfall data cannot show differences between neighbourhoods; the live forecast is a third-party model for one point and has missed extremes before.</li>
          <li>The 90 m elevation model includes buildings and has metre-scale error.</li>
          <li>The heavy-rain outlook is city-wide and about rain, not water on the road. It cannot change the plan between places, and tide is not included.</li>
          <li>BMC has split some wards (P/North → P/East + P/West; K/East → K/South + K/North); RainGuard uses the 24 older wards to match the boundary and incident data.</li>
        </ul>
        <p className="fine">
          RainGuard is a student prototype for HackAMatch 1.0, not an official BMC service or emergency-warning system. AI coding assistance was used during development.
          Data generated {data.generated_utc}.
        </p>
      </section>
    </div>
  );
}
