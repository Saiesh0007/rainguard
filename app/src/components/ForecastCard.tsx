import type { ForecastState } from "../lib/forecast";
import { imdCategory } from "../lib/forecast";
import EvidenceChip from "./EvidenceChip";
import Icon, { type IconName } from "./Icon";

const LEVEL_ICON: IconName[] = ["sun", "drizzle", "rain", "storm", "storm", "storm"];

export default function ForecastCard({ state }: { state: ForecastState }) {
  return (
    <section className="card forecast" aria-labelledby="fc-title">
      <div className="block__head">
        <h2 id="fc-title" className="h3">Rain outlook · next 3 days</h2>
        <EvidenceChip kind="forecast" />
      </div>
      {state.status === "loading" && (
        <ul className="days" aria-busy="true">
          {[0, 1, 2].map((i) => <li key={i} className="day skeleton" />)}
        </ul>
      )}
      {state.status === "error" && (
        <p className="muted" role="status">Forecast unavailable right now ({state.message}). The rest of RainGuard still works. <EvidenceChip kind="unknown" /></p>
      )}
      {state.status === "ok" && (
        <>
          {state.stale && <p className="warn" role="status">Showing a cached forecast from {new Date(state.forecast.fetchedAt).toLocaleString("en-IN")} — it may be out of date.</p>}
          <ul className="days">
            {state.forecast.days.map((d) => {
              const c = imdCategory(d.rainMm);
              return (
                <li key={d.date} className={`day day--${c.level}`}>
                  <span className="day__date">{new Date(d.date + "T00:00:00").toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short" })}</span>
                  <span className="day__mm"><Icon name={LEVEL_ICON[c.level]} size={18} />{d.rainMm === null ? "—" : `${d.rainMm.toFixed(1)} mm`}</span>
                  <span className="day__cat">{c.label}{d.probabilityPct !== null ? ` · ${d.probabilityPct}%` : ""}</span>
                </li>
              );
            })}
          </ul>
        </>
      )}
      <details className="fine-details">
        <summary>About this forecast</summary>
        <p className="fine">
          Third-party model forecast (Open-Meteo) for one point in Mumbai, labelled with IMD rain categories. It is not a RainGuard
          prediction, cannot show differences between neighbourhoods, and global models have under-estimated Mumbai's worst storms.
          For official warnings see <a href="https://mausam.imd.gov.in/" target="_blank" rel="noreferrer">IMD</a> and{" "}
          <a href="https://dm.mcgm.gov.in/" target="_blank" rel="noreferrer">BMC Disaster Management</a>.
        </p>
      </details>
    </section>
  );
}
