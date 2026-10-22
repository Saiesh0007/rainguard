import { useMemo, useState } from "react";
import type { DiagnosisId, RainGuardData, Weights } from "../types";
import { COMPONENTS, COMPONENT_LABEL, rescore } from "../lib/score";
import { diagnosisOf, inspectionPlan } from "../lib/allocate";
import Icon from "./Icon";
import DiagnosisChips from "./DiagnosisChips";
import { PRECISION_LABEL, SOURCE_SHORT, TIER_TEXT, sourcesOf } from "../lib/labels";

interface Props {
  data: RainGuardData;
  onOpen: (id: string) => void;
}

function toCsv(rows: string[][]): string {
  return rows.map((r) => r.map((c) => `"${c.replaceAll('"', '""')}"`).join(",")).join("\n");
}

function saveCsv(name: string, w: Weights, rows: string[][]) {
  const blob = new Blob([`# CityPulse RainGuard - decision support, not an official directive\n# weights: ${JSON.stringify(w)}\n` + toCsv(rows)], { type: "text/csv" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

const sameWeights = (a: Weights, b: Weights) => COMPONENTS.every((c) => Math.abs(a[c] - b[c]) < 1e-9);

export default function Civic({ data, onOpen }: Props) {
  const defaults = data.sensitivity.default_weights;
  const adjusted = data.sensitivity.population_adjusted_alternative.weights;
  const alloc = data.allocation;
  const labels = data.diagnosis.labels;
  const [w, setW] = useState<Weights>(defaults);
  const [k, setK] = useState(alloc.k);
  const [cap, setCap] = useState(alloc.cap_per_ward);
  const [ward, setWard] = useState("all");
  const [label, setLabel] = useState<"all" | DiagnosisId>("all");
  const [limit, setLimit] = useState(30);

  const scored = useMemo(() => rescore(data.locations, w), [data.locations, w]);
  const plan = useMemo(() => inspectionPlan(scored, k, cap), [scored, k, cap]);
  const planWards = new Set(plan.map((r) => r.loc.ward)).size;
  const core = new Set(alloc.stable_core);
  const isDefault = sameWeights(w, defaults);
  const isDefaultPlan = isDefault && k === alloc.k && cap === alloc.cap_per_ward;
  const total = COMPONENTS.reduce((s, c) => s + w[c], 0);
  const sens = data.sensitivity;
  const adj = sens.population_adjusted_alternative;

  const rows = scored
    .filter((r) => ward === "all" || r.loc.ward === ward)
    .filter((r) => label === "all" || diagnosisOf(r.loc).includes(label))
    .sort((a, b) => a.rank - b.rank || a.loc.location_id.localeCompare(b.loc.location_id));

  function downloadPlan() {
    saveCsv("rainguard_inspection_plan.csv", w, [
      ["order", "location_id", "name", "ward", "rank", "labels", "checks", "map_precision"],
      ...plan.map((r, i) => [
        String(i + 1), r.loc.location_id, r.loc.name, r.loc.ward, String(r.rank),
        diagnosisOf(r.loc).map((d) => labels[d].title).join("; "),
        diagnosisOf(r.loc).map((d) => labels[d].check).join("; "), r.loc.geocode_precision,
      ]),
    ]);
  }

  function downloadAll() {
    saveCsv("rainguard_inspection_priority.csv", w, [
      ["rank", "tier", "location_id", "name", "ward", "score", ...COMPONENTS, "lists", "pumps", "labels", "map_precision"],
      ...rows.map((r) => [
        String(r.rank), r.tier, r.loc.location_id, r.loc.name, r.loc.ward, r.score.toFixed(1),
        ...COMPONENTS.map((c) => (r.loc[c] === null ? "" : String(r.loc[c]))),
        sourcesOf(r.loc).map((s) => SOURCE_SHORT[s]).join("+"), r.loc.pumps === null ? "" : String(r.loc.pumps),
        diagnosisOf(r.loc).join("|"), r.loc.geocode_precision,
      ]),
    ]);
  }

  return (
    <div className="page">
      <header className="page__head">
        <h2>Weekly inspection plan</h2>
        <p className="lead">
          For BMC ward engineers and disaster-management teams: which of the {data.locations.length} officially listed places should
          your teams inspect this week, and what should they check there? It is <strong>decision support, not an official directive</strong>.
          The order is a relative rank, not a probability of flooding.
        </p>
      </header>

      <section className="card">
        <h3>This week's plan</h3>
        <div className="sliders">
          <label className="slider">
            <span>Places your teams can inspect</span>
            <input type="range" min={5} max={60} step={1} value={k} onChange={(e) => setK(Number(e.target.value))} />
            <output>{k}</output>
          </label>
          <label className="slider">
            <span>Most places from one ward</span>
            <input type="range" min={1} max={10} step={1} value={cap} onChange={(e) => setCap(Number(e.target.value))} />
            <output>{cap}</output>
          </label>
        </div>
        <p className="muted" aria-live="polite">
          {plan.length} places across {planWards} wards. Rule: walk down the priority order, skip a place if its ward is already at the
          maximum, and stop when the plan is full.
        </p>
        <div className="filters">
          <button className="btn" onClick={downloadPlan}><Icon name="download" size={16} />Download plan</button>
          {!isDefaultPlan && (
            <button className="btn btn--ghost" onClick={() => { setW(defaults); setK(alloc.k); setCap(alloc.cap_per_ward); }}>Back to the default plan</button>
          )}
        </div>
        <div className="table-scroll">
          <table className="data-table data-table--cards">
            <thead>
              <tr><th scope="col">#</th><th scope="col">Place</th><th scope="col">Ward</th><th scope="col">What to check</th>
                <th scope="col" title={`Share of ${alloc.n_weight_draws.toLocaleString()} random weightings in which the default plan (${alloc.k} places, ${alloc.cap_per_ward} per ward) included this place`}>Plan stability</th></tr>
            </thead>
            <tbody>
              {plan.map((r, i) => {
                const dx = diagnosisOf(r.loc);
                return (
                  <tr key={r.loc.location_id}>
                    <td data-label="#">{i + 1}</td>
                    <td data-label="Place" className="cell-place">
                      <button className="link-btn" onClick={() => onOpen(r.loc.location_id)}>{r.loc.name}</button>
                      <span className="fine block">rank {r.rank} · {PRECISION_LABEL[r.loc.geocode_precision]}</span>
                    </td>
                    <td data-label="Ward">{r.loc.ward}</td>
                    <td data-label="What to check" className="why">
                      <DiagnosisChips ids={dx} labels={labels} />
                      {dx.length > 0 ? <span className="block">{labels[dx[0]].check}</span> : <span className="block muted">Routine pre-monsoon check</span>}
                    </td>
                    <td data-label="Plan stability">
                      {Math.round(r.loc.plan_frequency * 100)}%{core.has(r.loc.location_id) && <span className="fine block">stable core</span>}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        <p className="fine">
          Which places make the plan depends on the weights: across {alloc.n_weight_draws.toLocaleString()} random weightings, the default plan's
          median overlap with the re-weighted plan was {alloc.plan_jaccard_vs_default.median} (Jaccard), and {alloc.stable_core.length} places
          were in it at least {Math.round(alloc.stable_core_threshold * 100)}% of the time. The labels and checks do not depend on the weights.
          Without the ward cap, the top {alloc.k} fall in only {alloc.wards_in_uncapped_top_k} wards; with it, {alloc.wards_in_default_plan}.
          Rain does not change this plan: free rainfall data has no neighbourhood detail, so every place gets the same city-wide outlook.
        </p>
      </section>

      <section className="card">
        <h3>How much should each factor count?</h3>
        <p className="muted">Drag to change the weights; the plan and the list update. Defaults are evidence-based: terrain is off because it showed no significant signal (Insights F4).</p>
        <div className="filters">
          <button className={`chip-btn ${sameWeights(w, defaults) ? "is-on" : ""}`} onClick={() => setW(defaults)}>Default: ward history as recorded</button>
          <button className={`chip-btn ${sameWeights(w, adjusted) ? "is-on" : ""}`} onClick={() => setW(adjusted)}>Adjust ward history for population</button>
        </div>
        <p className="fine">
          Recorded ward incidents mostly follow population (ρ = {data.evaluation.ward_level.spearman_population_vs_class.rho}), so the default
          favours wards where many people are exposed. The adjusted view uses only incidents beyond what population explains.
          The two orderings correlate at {adj.spearman_vs_default}; their top 20 overlap {adj.top20_jaccard_vs_default} (Jaccard).
        </p>
        <div className="sliders">
          {COMPONENTS.map((c) => (
            <label key={c} className="slider">
              <span>{COMPONENT_LABEL[c]}</span>
              <input type="range" min={0} max={1} step={0.05} value={w[c]}
                     onChange={(e) => setW({ ...w, [c]: Number(e.target.value) })} />
              <output>{total > 0 ? Math.round((w[c] / total) * 100) : 0}%</output>
            </label>
          ))}
        </div>
        {total === 0 && <p className="warn" role="alert">All weights are zero — every place scores 0. Raise at least one factor.</p>}
        <p className="fine">
          Robustness: across {sens.n_weight_draws.toLocaleString()} random weightings, the full ordering kept a median Spearman correlation of{" "}
          {sens.spearman_default_vs_random_weights.median} with the default, but the top-20 set changed a lot (median overlap{" "}
          {sens.top20_jaccard_default_vs_random_weights.median}, Jaccard). Treat tiers as a starting point for judgement.
        </p>
      </section>

      <section className="card">
        <h3>All listed places</h3>
        <div className="filters">
          <label>Ward
            <select value={ward} onChange={(e) => setWard(e.target.value)}>
              <option value="all">All wards</option>
              {data.wards.map((x) => <option key={x.ward} value={x.ward}>{x.ward}</option>)}
            </select>
          </label>
          <label>Label
            <select value={label} onChange={(e) => setLabel(e.target.value as "all" | DiagnosisId)}>
              <option value="all">Any label</option>
              {(Object.keys(labels) as DiagnosisId[]).map((d) => <option key={d} value={d}>{labels[d].title} ({labels[d].n})</option>)}
            </select>
          </label>
          <button className="btn" onClick={downloadAll}><Icon name="download" size={16} />Download CSV</button>
        </div>
        <p className="muted" aria-live="polite">{rows.length} places match.</p>
        {rows.length === 0 ? (
          <p className="empty">No places match these filters.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table data-table--cards">
              <thead>
                <tr><th scope="col">Rank</th><th scope="col">Place</th><th scope="col">Ward</th><th scope="col">Score</th>
                  <th scope="col">Labels</th><th scope="col">Pumps</th><th scope="col" title="Share of 2,000 random weightings (default analysis) in which this place made the top 20">Top-20 stability</th></tr>
              </thead>
              <tbody>
                {rows.slice(0, limit).map((r) => (
                  <tr key={r.loc.location_id}>
                    <td data-label="Rank"><span className="rank"><span className={`tier tier--${r.tier}`} title={TIER_TEXT[r.tier]}>{r.tier}</span>{r.rank}</span></td>
                    <td data-label="Place" className="cell-place">
                      <button className="link-btn" onClick={() => onOpen(r.loc.location_id)}>{r.loc.name}</button>
                      <span className="fine block">{PRECISION_LABEL[r.loc.geocode_precision]}</span>
                    </td>
                    <td data-label="Ward">{r.loc.ward}</td>
                    <td data-label="Score">{r.score.toFixed(1)}</td>
                    <td data-label="Labels" className="why"><DiagnosisChips ids={diagnosisOf(r.loc)} labels={labels} /></td>
                    <td data-label="Pumps">{r.loc.in_bmc_fpg_2026 ? (r.loc.pumps ?? "none") : "—"}</td>
                    <td data-label="Top-20 stability">{Math.round(r.loc.top20_frequency * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {rows.length > limit && <button className="btn btn--ghost" onClick={() => setLimit(limit + 50)}>Show more</button>}
      </section>
    </div>
  );
}
