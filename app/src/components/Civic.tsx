import { useMemo, useState } from "react";
import type { RainGuardData, Weights } from "../types";
import { COMPONENTS, COMPONENT_LABEL, rescore } from "../lib/score";
import { PRECISION_LABEL, SOURCE_SHORT, TIER_TEXT, sourcesOf } from "../lib/labels";

interface Props {
  data: RainGuardData;
  onOpen: (id: string) => void;
}

function toCsv(rows: string[][]): string {
  return rows.map((r) => r.map((c) => `"${c.replaceAll('"', '""')}"`).join(",")).join("\n");
}

export default function Civic({ data, onOpen }: Props) {
  const defaults = data.sensitivity.default_weights;
  const [w, setW] = useState<Weights>(defaults);
  const [ward, setWard] = useState("all");
  const [noPump, setNoPump] = useState(false);
  const [multi, setMulti] = useState(false);
  const [limit, setLimit] = useState(30);

  const scored = useMemo(() => rescore(data.locations, w), [data.locations, w]);
  const rows = scored
    .filter((r) => ward === "all" || r.loc.ward === ward)
    .filter((r) => !noPump || (r.loc.in_bmc_fpg_2026 && !r.loc.pumps))
    .filter((r) => !multi || r.loc.n_sources >= 2)
    .sort((a, b) => a.rank - b.rank || a.loc.location_id.localeCompare(b.loc.location_id));
  const isDefault = COMPONENTS.every((c) => Math.abs(w[c] - defaults[c]) < 1e-9);
  const total = COMPONENTS.reduce((s, c) => s + w[c], 0);
  const sens = data.sensitivity;

  function download() {
    const header = ["rank", "tier", "location_id", "name", "ward", "score", ...COMPONENTS, "lists", "pumps", "map_precision"];
    const body = rows.map((r) => [
      String(r.rank), r.tier, r.loc.location_id, r.loc.name, r.loc.ward, r.score.toFixed(1),
      ...COMPONENTS.map((c) => (r.loc[c] === null ? "" : String(r.loc[c]))),
      sourcesOf(r.loc).map((s) => SOURCE_SHORT[s]).join("+"), r.loc.pumps === null ? "" : String(r.loc.pumps),
      r.loc.geocode_precision,
    ]);
    const blob = new Blob([`# CityPulse RainGuard inspection priority - decision support, not an official directive\n# weights: ${JSON.stringify(w)}\n` + toCsv([header, ...body])], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "rainguard_inspection_priority.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  }

  return (
    <div className="page">
      <header className="page__head">
        <h2>Civic inspection priority</h2>
        <p className="lead">
          A transparent ordering of the {data.locations.length} officially listed places to help plan pre-monsoon inspections.
          It is <strong>decision support, not an official directive</strong>, and the score is a relative rank — not a probability of flooding.
        </p>
      </header>

      <section className="card">
        <h3>How much should each factor count?</h3>
        <p className="muted">Drag to change the weights and watch the order update. Defaults are evidence-based: terrain is off because it showed no significant signal (Insights F4).</p>
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
        {!isDefault && <button className="btn btn--ghost" onClick={() => setW(defaults)}>Reset to evidence-based defaults</button>}
        {total === 0 && <p className="warn" role="alert">All weights are zero — every place scores 0. Raise at least one factor.</p>}
        <p className="fine">
          Robustness: across {sens.n_weight_draws.toLocaleString()} random weightings, the full ordering kept a median Spearman correlation of{" "}
          {sens.spearman_default_vs_random_weights.median} with the default, but the top-20 set changed a lot (median overlap{" "}
          {sens.top20_jaccard_default_vs_random_weights.median}, Jaccard). Treat tiers as a starting point for judgement.
        </p>
      </section>

      <section className="card">
        <div className="filters">
          <label>Ward
            <select value={ward} onChange={(e) => setWard(e.target.value)}>
              <option value="all">All wards</option>
              {data.wards.map((x) => <option key={x.ward} value={x.ward}>{x.ward}</option>)}
            </select>
          </label>
          <label className="check"><input type="checkbox" checked={noPump} onChange={(e) => setNoPump(e.target.checked)} /> BMC spots with no pump listed</label>
          <label className="check"><input type="checkbox" checked={multi} onChange={(e) => setMulti(e.target.checked)} /> Named by 2+ lists</label>
          <button className="btn" onClick={download}>Download CSV</button>
        </div>
        <p className="muted" aria-live="polite">{rows.length} places match.</p>
        {rows.length === 0 ? (
          <p className="empty">No places match these filters.</p>
        ) : (
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr><th scope="col">Rank</th><th scope="col">Place</th><th scope="col">Ward</th><th scope="col">Score</th>
                  <th scope="col">Why</th><th scope="col">Pumps</th><th scope="col" title="Share of 2,000 random weightings (default analysis) in which this place made the top 20">Top-20 stability</th></tr>
              </thead>
              <tbody>
                {rows.slice(0, limit).map((r) => (
                  <tr key={r.loc.location_id}>
                    <td><span className={`tier tier--${r.tier}`} title={TIER_TEXT[r.tier]}>{r.tier}</span> {r.rank}</td>
                    <td>
                      <button className="link-btn" onClick={() => onOpen(r.loc.location_id)}>{r.loc.name}</button>
                      <span className="fine block">{PRECISION_LABEL[r.loc.geocode_precision]}</span>
                    </td>
                    <td>{r.loc.ward}</td>
                    <td>{r.score.toFixed(1)}</td>
                    <td className="why">
                      class {r.loc.incident_class}/7 ward · {r.loc.n_sources} list{r.loc.n_sources > 1 ? "s" : ""}
                      {r.loc.neighbours_1km !== null ? ` · ${r.loc.neighbours_1km} nearby` : ""}
                    </td>
                    <td>{r.loc.in_bmc_fpg_2026 ? (r.loc.pumps ?? "none") : "—"}</td>
                    <td>{Math.round(r.loc.top20_frequency * 100)}%</td>
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
