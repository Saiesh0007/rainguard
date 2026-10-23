import { lazy, Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { RainGuardData } from "./types";
import { loadForecast, type ForecastState } from "./lib/forecast";
import { CLASS_COLOR, INCIDENT_CLASS_RANGE, SOURCE_SHORT, isMapped, sourcesOf } from "./lib/labels";

const PRECISION_SHORT = { point: "Exact", street: "Along road", area: "Approximate", not_mappable: "List only" } as const;
import ForecastCard from "./components/ForecastCard";
import LocationPanel from "./components/LocationPanel";
import Insights from "./components/Insights";
import Civic from "./components/Civic";
import Method from "./components/Method";
import Home from "./components/Home";
import Icon, { type IconName } from "./components/Icon";

const MapView = lazy(() => import("./components/MapView"));

type Tab = "home" | "map" | "insights" | "civic" | "method";
const TABS: { id: Tab; label: string; icon: IconName }[] = [
  { id: "home", label: "Home", icon: "drop" },
  { id: "map", label: "Map", icon: "map" },
  { id: "insights", label: "Insights", icon: "chart" },
  { id: "civic", label: "Plan", icon: "shield" },
  { id: "method", label: "Method", icon: "info" },
];
const STALE_DATA_DAYS = 365;

/** Deep links: #place=RG-081 or #tab=insights - shareable views for teammates and judges. No hash = landing page. */
function readHash(): { tab: Tab; place: string | null } {
  const p = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const place = p.get("place");
  const tab = (p.get("tab") as Tab) ?? (place ? "map" : "home");
  return { tab: TABS.some((t) => t.id === tab) ? tab : "home", place };
}

function useTheme(): [boolean, () => void] {
  const [dark, setDark] = useState<boolean>(() => {
    try {
      const saved = localStorage.getItem("rainguard.theme");
      if (saved) return saved === "dark";
    } catch { /* storage unavailable */ }
    return window.matchMedia?.("(prefers-color-scheme: dark)")?.matches ?? false;
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
  const initial = useMemo(readHash, []);
  const [data, setData] = useState<RainGuardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastState>({ status: "loading" });
  const [tab, setTab] = useState<Tab>(initial.tab);
  const [selected, setSelected] = useState<string | null>(initial.place);
  const [query, setQuery] = useState("");
  const [showWards, setShowWards] = useState(true);
  const [view, setView] = useState<"map" | "list">("map");
  const [dark, toggleTheme] = useTheme();
  const searchRef = useRef<HTMLInputElement>(null);

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

  // keep the URL in sync so any view can be shared
  useEffect(() => {
    const h = selected && tab === "map" ? `#place=${selected}` : tab !== "home" ? `#tab=${tab}` : "";
    if (window.location.hash !== h) history.replaceState(null, "", h || window.location.pathname + window.location.search);
  }, [tab, selected]);

  const close = useCallback(() => setSelected(null), []);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") close(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [close]);

  const filtered = useMemo(() => {
    if (!data) return [];
    const q = query.trim().toLowerCase();
    if (!q) return data.locations;
    return data.locations.filter((l) => `${l.name} ${l.detail ?? ""} ward ${l.ward}`.toLowerCase().includes(q));
  }, [data, query]);

  if (error) {
    return (
      <main className="state" role="alert">
        <div className="state__icon"><Icon name="alert" size={28} /></div>
        <h1>CityPulse RainGuard</h1>
        <p>The analysis data could not be loaded ({error}). Run <code>python analysis/run_pipeline.py</code> and reload.</p>
      </main>
    );
  }
  if (!data) {
    return (
      <main className="state" aria-busy="true">
        <div className="state__icon state__icon--pulse"><Icon name="drop" size={28} /></div>
        <h1>CityPulse RainGuard</h1>
        <p className="muted">Loading evidence…</p>
      </main>
    );
  }

  const selectedLoc = data.locations.find((l) => l.location_id === selected) ?? null;
  const ageDays = (Date.now() - new Date(data.generated_utc).getTime()) / 86_400_000;
  const mappedCount = filtered.filter(isMapped).length;
  const multi = data.locations.filter((l) => l.n_sources >= 2).length;
  const openLocation = (id: string) => { setSelected(id); setTab("map"); };
  const goTab = (t: Tab) => { setTab(t); window.scrollTo({ top: 0 }); };

  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true"><Icon name="drop" size={20} /></span>
          <div>
            <h1>CityPulse <span className="brand__accent">RainGuard</span></h1>
            <p className="brand__tag">Mumbai waterlogging evidence · Discover · Explain · Act</p>
          </div>
        </div>
        <nav className="tabs" aria-label="Sections">
          {TABS.map((t) => (
            <button key={t.id} className={`tab ${tab === t.id ? "is-active" : ""}`} aria-current={tab === t.id ? "page" : undefined} onClick={() => goTab(t.id)}>
              <Icon name={t.icon} size={20} className="tab__icon" /><span>{t.label}</span>
            </button>
          ))}
        </nav>
        <button className="icon-btn" onClick={toggleTheme} aria-label={`Switch to ${dark ? "light" : "dark"} theme`}>
          <Icon name={dark ? "sun" : "moon"} size={18} />
        </button>
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
              <section className="card summary" aria-label="Summary">
                <ul className="kpis">
                  <li><strong className="kpi__v">{data.locations.length}</strong><span className="kpi__l">official flood-prone places</span></li>
                  <li><span className="kpi__v">{multi}</span><span className="kpi__l">on 2+ official lists</span></li>
                  <li><span className="kpi__v">3</span><span className="kpi__l">lists: BMC, BEST, Traffic Police</span></li>
                </ul>
                <p className="summary__note">
                  <Icon name="info" size={16} /><span>Shows where water is <em>expected</em> in heavy rain — not live flooding, and not a safety guarantee.</span>
                </p>
              </section>

              <section className="toolbar" aria-label="Search and view">
                <label className="search">
                  <Icon name="search" size={18} className="search__icon" />
                  <span className="sr-only">Search places or wards</span>
                  <input ref={searchRef} type="search" placeholder="Search a place or ward (e.g. Hindmata, L)" value={query} onChange={(e) => setQuery(e.target.value)} />
                  {query && <button className="search__clear" onClick={() => { setQuery(""); searchRef.current?.focus(); }} aria-label="Clear search"><Icon name="close" size={16} /></button>}
                </label>
                <div className="toolbar__row">
                  <div className="seg" role="group" aria-label="View">
                    <button className={view === "map" ? "is-active" : ""} aria-pressed={view === "map"} onClick={() => setView("map")}><Icon name="map" size={16} />Map</button>
                    <button className={view === "list" ? "is-active" : ""} aria-pressed={view === "list"} onClick={() => setView("list")}><Icon name="list" size={16} />List</button>
                  </div>
                  <button className={`chip-btn ${showWards ? "is-on" : ""}`} aria-pressed={showWards} aria-label="Toggle ward incident shading" onClick={() => setShowWards((s) => !s)}>
                    <Icon name="layers" size={16} /> History
                  </button>
                </div>
                <p className="muted small" aria-live="polite">{filtered.length} places · {mappedCount} on map{filtered.length - mappedCount ? ` · ${filtered.length - mappedCount} list-only` : ""}</p>
              </section>

              <ForecastCard state={forecast} track={data.outlook.forecast_track_record} />
              <Legend show={showWards} />
            </aside>

            <section className="stage" aria-label="Locations">
              {view === "map" ? (
                <Suspense fallback={<div className="map-wrap"><div className="map-overlay">Loading map…</div></div>}>
                  <MapView locations={filtered} wards={data.wards} selectedId={selected} onSelect={setSelected} showWards={showWards} dark={dark} />
                  <div className="map-key" aria-hidden="true">
                    <span><span className="sw sw--dot" /> Exact / road</span>
                    <span><span className="sw sw--ring" /> Approximate</span>
                  </div>
                </Suspense>
              ) : (
                <ul className="loc-list">
                  {filtered.length === 0 && <li className="empty">No listed place matches “{query}”. That does not mean the area is safe — it may simply not be on these lists.</li>}
                  {[...filtered].sort((a, b) => a.ward.localeCompare(b.ward) || a.name.localeCompare(b.name)).map((l) => (
                    <li key={l.location_id}>
                      <button className={`loc ${selected === l.location_id ? "is-active" : ""}`} onClick={() => setSelected(l.location_id)}>
                        <span className="loc__ward" aria-label={`Ward ${l.ward}`}>{l.ward}</span>
                        <span className="loc__body">
                          <span className="loc__name">{l.name}</span>
                          <span className="loc__meta">{l.detail ? `${l.detail} · ` : ""}{sourcesOf(l).map((s) => SOURCE_SHORT[s]).join(" + ")} · {PRECISION_SHORT[l.geocode_precision]}</span>
                        </span>
                        {l.n_sources > 1 && <span className="loc__badge">{l.n_sources} lists</span>}
                        <Icon name="chevron" size={18} className="loc__chev" />
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
              <>
                <div className="backdrop" onClick={close} aria-hidden="true" />
                <div className="sheet" role="dialog" aria-modal="false" aria-label={`Details for ${selectedLoc.name}`}>
                  <div className="sheet__handle" aria-hidden="true" />
                  <LocationPanel loc={selectedLoc} forecast={forecast} nLocations={data.locations.length} labels={data.diagnosis.labels} onClose={close} />
                </div>
              </>
            )}
          </div>
        )}
        {tab === "home" && <Home data={data} forecast={forecast} onGo={goTab} onOpen={openLocation} />}
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
          <p className="fine">Ward shading: recorded waterlogging incidents, 2016–2023/25 (BMC). Mostly follows population.</p>
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
