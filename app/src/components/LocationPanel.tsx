import { useEffect, useRef, useState } from "react";
import type { Location } from "../types";
import Icon from "./Icon";
import type { ForecastState } from "../lib/forecast";
import { imdCategory } from "../lib/forecast";
import EvidenceChip from "./EvidenceChip";
import {
  INCIDENT_CLASS_RANGE, PRECISION_LABEL, SOURCE_LABEL, TIER_TEXT, sourcesOf,
} from "../lib/labels";
import { COMPONENT_LABEL, COMPONENTS } from "../lib/score";

interface Props {
  loc: Location;
  forecast: ForecastState;
  nLocations: number;
  onClose: () => void;
}

function maxForecast(f: ForecastState): number | null {
  if (f.status !== "ok") return null;
  const v = f.forecast.days.map((d) => d.rainMm).filter((x): x is number => x !== null);
  return v.length ? Math.max(...v) : null;
}

export default function LocationPanel({ loc, forecast, nLocations, onClose }: Props) {
  const srcs = sourcesOf(loc);
  const peak = maxForecast(forecast);
  const cat = imdCategory(peak);
  const precise = loc.geocode_precision === "point" || loc.geocode_precision === "street";
  const diversions = loc.traffic_diversion ? loc.traffic_diversion.split(" || ") : [];
  const [copied, setCopied] = useState(false);
  const titleRef = useRef<HTMLHeadingElement>(null);
  // move focus into the panel when a new place opens (keyboard and screen-reader users)
  useEffect(() => { titleRef.current?.focus({ preventScroll: true }); }, [loc.location_id]);

  async function share() {
    const url = `${window.location.origin}${window.location.pathname}#place=${loc.location_id}`;
    try {
      if (navigator.share) await navigator.share({ title: `${loc.name} · RainGuard`, url });
      else {
        await navigator.clipboard.writeText(url);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2000);
      }
    } catch { /* user cancelled share sheet */ }
  }

  return (
    <article className="panel" aria-labelledby="panel-title">
      <header className="panel__head">
        <div className="panel__title">
          <p className="eyebrow">Ward {loc.ward} · {loc.location_id}</p>
          <h2 id="panel-title" tabIndex={-1} ref={titleRef}>{loc.name}</h2>
          {loc.detail && <p className="muted">{loc.detail}</p>}
        </div>
        <button className="icon-btn" onClick={onClose} aria-label="Close details"><Icon name="close" size={18} /></button>
      </header>
      <div className="panel__actions">
        <button className="btn btn--soft" onClick={share}><Icon name="share" size={16} />{copied ? "Link copied" : "Share"}</button>
        {loc.lat !== null && loc.lon !== null && (
          <a className="btn btn--soft" href={`https://www.openstreetmap.org/?mlat=${loc.lat}&mlon=${loc.lon}#map=17/${loc.lat}/${loc.lon}`} target="_blank" rel="noreferrer">
            <Icon name="pin" size={16} />View on OpenStreetMap
          </a>
        )}
        <a className="btn btn--soft" href="tel:1916"><Icon name="phone" size={16} />BMC 1916</a>
      </div>

      <section className="panel__summary">
        <p>
          Named on <strong>{loc.n_sources} of 3</strong> official waterlogging lists for 2026. This means
          authorities expect water here in heavy rain — <strong>not</strong> that it is flooded right now.
        </p>
      </section>

      <section className="block">
        <div className="block__head"><h3>What the official records say</h3><EvidenceChip kind="historical" /></div>
        <ul className="source-list">
          {srcs.map((s) => <li key={s}>{SOURCE_LABEL[s] ?? s}</li>)}
        </ul>
        {diversions.length > 0 && (
          <div className="callout">
            <p className="callout__title">Traffic police plan if this spot waterlogs</p>
            {diversions.map((d, i) => <p key={i}>Diverted via: {d}</p>)}
          </div>
        )}
        <p className="fine">Source rows: {loc.record_ids.replaceAll("|", ", ")}</p>
      </section>

      <section className="block">
        <div className="block__head"><h3>Ward {loc.ward} incident history</h3><EvidenceChip kind="historical" /></div>
        <div className="meter" aria-hidden="true">
          {[1, 2, 3, 4, 5, 6, 7].map((c) => (
            <span key={c} className={`meter__seg ${c <= loc.incident_class ? "is-on" : ""}`} />
          ))}
        </div>
        <p>
          Class <strong>{loc.incident_class} of 7</strong> — about {INCIDENT_CLASS_RANGE[loc.incident_class]} recorded
          waterlogging incidents in the whole ward (BMC map, 2016–2023/25).
        </p>
        <p className="fine">Ward-level only: every place in the ward gets the same value. Counts reflect complaints as well as flooding.</p>
      </section>

      <section className="block">
        <div className="block__head"><h3>Rain outlook for Mumbai</h3><EvidenceChip kind="forecast" /></div>
        {forecast.status === "loading" && <p className="muted">Loading forecast…</p>}
        {forecast.status === "error" && <p className="muted">Forecast unavailable ({forecast.message}). <EvidenceChip kind="unknown" /></p>}
        {forecast.status === "ok" && (
          <p>
            Highest daily rain in the next 3 days: <strong>{peak?.toFixed(1) ?? "—"} mm</strong> ({cat.label}).
            {forecast.stale && <span className="warn"> Cached forecast — may be out of date.</span>}
          </p>
        )}
        <p className="fine">Open-Meteo model forecast for one city point. Global models have badly under-estimated Mumbai's extreme rain before (see Insights, F3). Check IMD and BMC alerts.</p>
      </section>

      <section className="block">
        <div className="block__head"><h3>Map position</h3><EvidenceChip kind={loc.geocode_precision === "not_mappable" ? "unknown" : "estimated"} /></div>
        <p><strong>{PRECISION_LABEL[loc.geocode_precision]}</strong>{loc.geocode_osm_name ? ` — matched to “${loc.geocode_osm_name.split(",").slice(0, 3).join(",")}”` : ""}.</p>
        {loc.geocode_note && <p className="fine">Review note: {loc.geocode_note}</p>}
      </section>

      <section className="block">
        <div className="block__head"><h3>Terrain</h3><EvidenceChip kind={precise && loc.elevation_m !== null ? "estimated" : "unknown"} /></div>
        {precise && loc.elevation_m !== null ? (
          <p>
            About {loc.elevation_m} m above sea level; {loc.tpi_m !== null && loc.tpi_m < 0 ? `${Math.abs(loc.tpi_m)} m lower` : `${loc.tpi_m ?? 0} m higher`} than
            the land within 1 km (90 m elevation model).
          </p>
        ) : (
          <p className="muted">Not assessed — the location is only known approximately.</p>
        )}
        <p className="fine">Unvalidated: across all precise listed spots, terrain did not significantly differ from the rest of their ward. Not a flood-depth estimate.</p>
      </section>

      <section className="block">
        <div className="block__head"><h3>Dewatering pumps</h3><EvidenceChip kind={loc.in_bmc_fpg_2026 ? "historical" : "unknown"} /></div>
        {loc.in_bmc_fpg_2026 ? (
          loc.pumps ? (
            <p>{loc.pumps} pump{loc.pumps > 1 ? "s" : ""} listed by BMC
              {loc.capacity_listed_m3hr ? `, ${loc.capacity_listed_m3hr} m³/h listed capacity${loc.capacity_complete ? "" : " (incomplete)"}` : ""}.
              {loc.project_category ? ` Status: ${loc.project_category}.` : ""}</p>
          ) : (
            <p>No pump listed by BMC for this spot.{loc.project_category ? ` Status: ${loc.project_category}.` : ""}</p>
          )
        ) : (
          <p className="muted">Not in BMC's 2026 list, so pump information is unknown.</p>
        )}
      </section>

      <section className="block block--act">
        <h3>What you can do</h3>
        <ul className="act-list">
          {cat.level >= 3 && <li><strong>Heavy rain is forecast.</strong> If you can, avoid travelling through this spot during the heaviest rain; BMC notes flooding is worst when intense rain coincides with high tide.</li>}
          {diversions.length > 0 && <li>Expect the traffic diversion above if water collects here.</li>}
          <li>Do not walk or drive through standing water — depth and open drains are hidden.</li>
          <li>If you do wade through floodwater, BMC's public-health guidance advises seeing a doctor within 24–72 hours about leptospirosis prevention.</li>
          <li>Report waterlogging or emergencies to the BMC helpline <a href="tel:1916">1916</a>; follow <a href="https://dm.mcgm.gov.in/" target="_blank" rel="noreferrer">dm.mcgm.gov.in</a> and @mybmc for official alerts.</li>
          <li>A road that is <em>not</em> on these lists is not guaranteed to be safe.</li>
        </ul>
      </section>

      <details className="block">
        <summary><h3 className="inline">Inspection priority (for civic teams)</h3></summary>
        <p>
          Rank <strong>{loc.priority_rank}</strong> of {nLocations} · score {loc.priority_score.toFixed(1)} / 100 ·
          tier {loc.priority_tier} ({TIER_TEXT[loc.priority_tier]}). <EvidenceChip kind="estimated" />
        </p>
        <ul className="bars">
          {COMPONENTS.map((c) => {
            const v = loc[c];
            return (
              <li key={c}>
                <span className="bars__label">{COMPONENT_LABEL[c]}</span>
                <span className="bars__track">{v !== null && <span className="bars__fill" style={{ width: `${v * 100}%` }} />}</span>
                <span className="bars__val">{v === null ? "n/a" : v.toFixed(2)}</span>
              </li>
            );
          })}
        </ul>
        <p className="fine">
          Under 2,000 random weightings this place ranked between {loc.rank_p10} and {loc.rank_p90} (10th–90th percentile)
          and was in the top 20 in {(loc.top20_frequency * 100).toFixed(0)}% of them. A relative ordering for planning — not a probability of flooding.
        </p>
      </details>
    </article>
  );
}
