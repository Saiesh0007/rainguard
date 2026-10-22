import type { RainGuardData } from "../types";
import EvidenceChip from "./EvidenceChip";
import { EVIDENCE, type EvidenceKind } from "../lib/labels";

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
