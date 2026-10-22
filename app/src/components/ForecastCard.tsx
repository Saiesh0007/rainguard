import type { ForecastState } from "../lib/forecast";
import { imdCategory, trackBand } from "../lib/forecast";
import type { Outlook } from "../types";
import EvidenceChip from "./EvidenceChip";
import Icon, { type IconName } from "./Icon";

const LEVEL_ICON: IconName[] = ["sun", "drizzle", "rain", "storm", "storm", "storm"];

function TrackRecord({ state, track }: { state: ForecastState; track: Outlook["forecast_track_record"] }) {
  if (state.status !== "ok" || state.forecast.days.length < 2) return null;
  const tomorrow = state.forecast.days[1];
  const band = trackBand(tomorrow.rainMm);
  const month = new Date(tomorrow.date + "T00:00:00").getMonth() + 1;
  if (band === null) return null;
  if (month < 6 || month > 9) {
    return <p className="fine">Track record: measured for June–September only ({track.period}), so none is shown for this date.</p>;
  }
  const row = track.by_forecast_amount[band];
  return (
    <p className="track">
      Tomorrow's forecast is in the <strong>{row.forecast}</strong> band. In the {track.years.join(" and ")} monsoons,
      {" "}{row.heavy_days} of {row.n_days} days forecast like this turned out to be heavy-rain days (IMD ≥ 64.5 mm).
    </p>
  );
}

export default function ForecastCard({ state, track }: { state: ForecastState; track: Outlook["forecast_track_record"] }) {
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
          <TrackRecord state={state} track={track} />
        </>
      )}
      <details className="fine-details">
        <summary>About this forecast</summary>
        <p className="fine">
          Third-party model forecast (Open-Meteo) for one point in Mumbai, labelled with IMD rain categories. It is not a RainGuard
          prediction, cannot show differences between neighbourhoods, and global models have under-estimated Mumbai's worst storms.
          The track record compares archived day-ahead forecasts with observed IMD rain (Method tab).
          For official warnings see <a href="https://mausam.imd.gov.in/" target="_blank" rel="noreferrer">IMD</a> and{" "}
          <a href="https://dm.mcgm.gov.in/" target="_blank" rel="noreferrer">BMC Disaster Management</a>.
        </p>
      </details>
    </section>
  );
}
