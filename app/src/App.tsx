import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { RainGuardData } from "./types";
import { loadForecast, type ForecastState } from "./lib/forecast";
import { CLASS_COLOR, INCIDENT_CLASS_RANGE, PRECISION_LABEL, SOURCE_SHORT, isMapped, sourcesOf } from "./lib/labels";
import ForecastCard from "./components/ForecastCard";
import LocationPanel from "./components/LocationPanel";
import Insights from "./components/Insights";
import Civic from "./components/Civic";
import Method from "./components/Method";

const MapView = lazy(() => import("./components/MapView"));

type Tab = "map" | "insights" | "civic" | "method";
const TABS: { id: Tab; label: string; icon: string }[] = [
  { id: "map", label: "Map", icon: "◎" },
  { id: "insights", label: "Insights", icon: "▤" },
  { id: "civic", label: "Civic", icon: "☰" },
  { id: "method", label: "Method", icon: "ⓘ" },
];
const STALE_DATA_DAYS = 365;

function useTheme(): [boolean, () => void] {
  const media = typeof window !== "undefined" ? window.matchMedia("(prefers-color-scheme: dark)") : null;
  const [dark, setDark] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem("rainguard.theme");
      if (saved) return saved === "dark";
    } catch { /* ignore */ }
    return media?.matches ?? false;
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
  }, [dark]);
  return [dark, () => setDark((d) => {
    try { localStorage.setItem("rainguard.theme", d ? "light" : "dark"); } catch { /* ignore */ }
    return !d;
  })];
}

export default function App() {
  const [data, setData] = useState<RainGuardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastState>({ status: "loading" });
  const [tab, setTab] = useState<Tab>("map");
  const [selected, setSelected] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [showWards, setShowWards] = useState(true);
  const [view, setView] = useState<"map" | "list">("map");
  const [dark, toggleTheme] = useTheme();

  useEffect(() => {
    fetch(`${import.meta.env.BASE_URL}data/rainguard.json`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(String(e)));
    loadForecast().then(setForecast);
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    if (!q) return data.locations;
    return data.locations.filter((l) =>
      `${l.name} ${l.detail ?? ""} ward ${l.ward} ${l.ward}`.toLowerCase().includes(q));
  }, [data, query]);

  if (error) {
    return (
      <main className="state" role="alert">
        <h1>CityPulse RainGuard</h1>
        <p>The analysis data could not be loaded ({error}). Run <code>python analysis/run_pipeline.py</code> and reload.</p>
      </main>
    );
  }
  if (!data) {
    return <main className="state" aria-busy="true"><h1>CityPulse RainGuard</h1><p>Loading evidence…</p></main>;
  }

  const selectedLoc = data.locations.find((l) => l.location_id === selected) ?? null;
  const ageDays = (Date.now() - new Date(data.generated_utc).getTime()) / 86_400_000;
  const mappedCount = filtered.filter(isMapped).length;
  const openLocation = (id: string) => { setSelected(id); setTab("map"); };

  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="22" height="22"><path d="M12 2.5c-3.6 4.6-6.5 8.4-6.5 11.8a6.5 6.5 0 0 0 13 0C18.5 10.9 15.6 7.1 12 2.5Z" fill="currentColor" /></svg>
          </span>
          <div>
            <h1>CityPulse RainGuard</h1>
            <p className="brand__tag">Mumbai waterlogging evidence · Discover · Explain · Act</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} className={`tab ${tab === t.id ? "is-active" : ""}`} aria-current={tab === t.id ? "page" : undefined} onClick={() => setTab(t.id)}>
              <span aria-hidden="true" className="tab__icon">{t.icon}</span><span>{t.label}</span>
            </button>
          ))}
        </nav>
        <button className="icon-btn theme-btn" onClick={toggleTheme} aria-label={`Switch to ${dark ? "light" : "dark"} theme`}>{dark ? "☀" : "☾"}</button>
      </header>

      {ageDays > STALE_DATA_DAYS && (
        <div className="banner banner--warn" role="status">
          These official lists were compiled {Math.floor(ageDays)} days ago and may be out of date. Check BMC's latest Flood Preparedness Guidelines.
        </div>
      )}

      <main id="main">
        {tab === "map" && (
          <div className="map-layout">
            <aside className="side">
              <section className="card intro">
                <p>
                  <strong>{data.locations.length}</strong> places named on <strong>three official 2026 lists</strong> of
                  waterlogging-prone spots (BMC, BEST and Mumbai Traffic Police). Only {data.cleaning.by_n_sources["2"] + (data.cleaning.by_n_sources["3"] ?? 0)} appear on more than one list.
                  RainGuard shows where water is <em>expected</em>, not where it is right now.
                </p>
              </section>
              <ForecastCard state={forecast} />
              <section className="card controls">
                <label className="search">
                  <span className="sr-only">Search places or wards</span>
                  <input type="search" placeholder="Search a place or ward (e.g. Hindmata, L)" value={query} onChange={(e) => setQuery(e.target.value)} />
                </label>
                <div className="seg" role="group" aria-label="View">
                  <button className={view === "map" ? "is-active" : ""} aria-pressed={view === "map"} onClick={() => setView("map")}>Map</button>
                  <button className={view === "list" ? "is-active" : ""} aria-pressed={view === "list"} onClick={() => setView("list")}>List</button>
                </div>
                <label className="check"><input type="checkbox" checked={showWards} onChange={(e) => setShowWards(e.target.checked)} /> Ward incident history</label>
                <p className="muted" aria-live="polite">{filtered.length} places · {mappedCount} on map{filtered.length - mappedCount ? ` · ${filtered.length - mappedCount} list-only` : ""}</p>
              </section>
              <Legend show={showWards} />
            </aside>

            <section className="stage" aria-label="Locations">
              {view === "map" ? (
                <Suspense fallback={<div className="map-wrap"><div className="map-overlay">Loading map…</div></div>}>
                  <MapView locations={filtered} wards={data.wards} selectedId={selected} onSelect={setSelected} showWards={showWards} dark={dark} />
                </Suspense>
              ) : (
                <ul className="loc-list">
                  {filtered.length === 0 && <li className="empty">No listed place matches “{query}”. That does not mean the area is safe — it may simply not be on these lists.</li>}
                  {[...filtered].sort((a, b) => a.ward.localeCompare(b.ward) || a.name.localeCompare(b.name)).map((l) => (
                    <li key={l.location_id}>
                      <button className={`loc ${selected === l.location_id ? "is-active" : ""}`} onClick={() => setSelected(l.location_id)}>
                        <span className="loc__name">{l.name}</span>
                        <span className="loc__meta">Ward {l.ward} · {sourcesOf(l).map((s) => SOURCE_SHORT[s]).join(" + ")} · {PRECISION_LABEL[l.geocode_precision]}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              {query && filtered.length === 0 && view === "map" && (
                <div className="map-note" role="status">No listed place matches “{query}”. Not being listed does not mean safe.</div>
              )}
            </section>

            {selectedLoc && (
              <div className="sheet" role="dialog" aria-modal="false" aria-label={`Details for ${selectedLoc.name}`}>
                <LocationPanel loc={selectedLoc} forecast={forecast} nLocations={data.locations.length} onClose={() => setSelected(null)} />
              </div>
            )}
          </div>
        )}
        {tab === "insights" && <Insights data={data} />}
        {tab === "civic" && <Civic data={data} onOpen={openLocation} />}
        {tab === "method" && <Method data={data} />}
      </main>

      <footer className="footer">
        <p>Student prototype for HackAMatch 1.0 — not an official BMC service or emergency warning. Emergencies: BMC helpline <a href="tel:1916">1916</a>.</p>
        <p className="fine">Data: BMC, BEST, Mumbai Traffic Police (2026 publications), IMD via OpenCity, ERA5 &amp; Copernicus DEM via Open-Meteo (CC BY 4.0), ward boundaries © DataMeet (CC BY-SA 2.5 IN), map © OpenMapTiles © OpenStreetMap contributors.</p>
      </footer>
    </div>
  );
}

function Legend({ show }: { show: boolean }) {
  return (
    <section className="card legend" aria-label="Map legend">
      <h2 className="h3">Legend</h2>
      <ul>
        <li><span className="sw sw--dot" aria-hidden="true" /> Listed place (exact or road-level). Bigger = on more lists</li>
        <li><span className="sw sw--ring" aria-hidden="true" /> Listed place, neighbourhood only (approximate)</li>
      </ul>
      {show && (
        <>
          <p className="fine">Ward fill: recorded waterlogging incidents, 2016–2023/25 (BMC). Mostly follows population.</p>
          <ul className="ramp">
            {[1, 2, 3, 4, 5, 6, 7].map((c) => (
              <li key={c}><span className="sw" style={{ background: CLASS_COLOR[c] }} aria-hidden="true" />{INCIDENT_CLASS_RANGE[c]}</li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}
