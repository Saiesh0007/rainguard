import type { RainGuardData, Finding } from "../types";
import BarChart from "./BarChart";
import EvidenceChip from "./EvidenceChip";
import { CLASS_COLOR, INCIDENT_CLASS_RANGE, SOURCE_SHORT, formatInt, isMapped } from "../lib/labels";
import type { EvidenceKind } from "../lib/labels";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function kinds(f: Finding): EvidenceKind[] {
  const t = f.evidence_type.toLowerCase();
  return (["observed", "historical", "estimated", "forecast"] as EvidenceKind[]).filter((k) => t.includes(k));
}

function Card({ f, children }: { f: Finding; children: React.ReactNode }) {
  return (
    <article className="finding" id={f.id}>
      <header>
        <p className="eyebrow">{f.id} · {kinds(f).map((k) => <EvidenceChip key={k} kind={k} />)}</p>
        <h3>{f.title}</h3>
      </header>
      {children}
      <dl className="meta">
        <div><dt>Method</dt><dd>{f.method}</dd></div>
        <div><dt>Period</dt><dd>{f.period}</dd></div>
        <div><dt>Sample</dt><dd>{f.sample}</dd></div>
      </dl>
      <details>
        <summary>Caveats</summary>
        <ul>{f.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </details>
    </article>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <div className="stat">
      <span className="stat__value">{value}</span>
      <span className="stat__label">{label}</span>
    </div>
  );
}

export default function Insights({ data }: { data: RainGuardData }) {
  const byId = Object.fromEntries(data.findings.map((f) => [f.id, f]));
  const wards = [...data.wards].sort((a, b) => b.incident_class - a.incident_class || b.population_2011 - a.population_2011);
  const f2n = byId.F2.numbers as { by_source_combination: Record<string, number>; best_rows_per_ward_where_bmc_lists_nil: Record<string, number> };
  const rain = data.rainfall.summary;
  const precise = data.locations.filter((l) => isMapped(l) && (l.geocode_precision === "point" || l.geocode_precision === "street") && l.tpi_pct_in_ward !== null);
  const bins = Array.from({ length: 10 }, (_, i) => precise.filter((l) => Math.min(9, Math.floor((l.tpi_pct_in_ward as number) * 10)) === i).length);
  const f4 = data.evaluation.location_terrain_case_control.point_or_street;
  const f5 = byId.F5.numbers as Record<string, number>;
  const f1 = byId.F1.numbers as Record<string, unknown>;

  return (
    <div className="page">
      <header className="page__head">
        <h2>Insights</h2>
        <p className="lead">Five findings computed from the real data by <code>analysis/eda.py</code>. Each lists its method, period, sample and caveats.</p>
      </header>

      <Card f={byId.F1}>
        <div className="stats">
          <Stat value={String(f1.n_wards_top_class)} label="wards in the top class (467–800 incidents)" />
          <Stat value={`${Math.round(Number(f1.share_population_in_class_6_or_7_wards) * 100)}%`} label="of Mumbai's 2011 population lives in class 6–7 wards" />
        </div>
        <BarChart
          title="Waterlogging incident class by ward"
          orientation="horizontal"
          valueLabel="incident class"
          maxValue={7}
          ticks={[0, 1, 2, 3, 4, 5, 6, 7]}
          bars={wards.map((w) => ({
            label: w.ward, value: w.incident_class, color: CLASS_COLOR[w.incident_class],
            tip: `Class ${w.incident_class} (${INCIDENT_CLASS_RANGE[w.incident_class]} incidents) · population ${formatInt(w.population_2011)}`,
          }))}
        />
      </Card>

      <Card f={byId.F2}>
        <BarChart
          title="Distinct locations by which official lists name them"
          orientation="horizontal"
          valueLabel="locations"
          bars={Object.entries(f2n.by_source_combination).sort((a, b) => b[1] - a[1]).map(([k, v]) => ({
            label: k.split("|").map((s) => SOURCE_SHORT[s] ?? s).join(" + "),
            value: v,
            color: k.includes("|") ? "var(--series-2)" : "var(--series-1)",
          }))}
        />
        <p className="note">
          BMC's 2026 list says wards A, B and G/N have <strong>no</strong> waterlogging spots, while BEST lists{" "}
          {Object.entries(f2n.best_rows_per_ward_where_bmc_lists_nil).map(([w, n]) => `${n} in ${w}`).join(", ")}.
          The BEST list is virtually unchanged across its 2023-24, 2024-25 and 2026 editions.
        </p>
      </Card>

      <Card f={byId.F3}>
        <div className="stats">
          <Stat value={`${Math.round(rain.imd.jjas_share_of_annual * 1000) / 10}%`} label="of annual rain falls in June–September (IMD, 1901–2021)" />
          <Stat value={`${rain.era5["2005_07_26_mm"]} mm`} label={`ERA5 model rain for 26 July 2005 — BMC records ${rain.era5["2005_07_26_reference_mm"]} mm at Santacruz`} />
          <Stat value={`${Math.round(rain.era5_vs_imd_monthly_1991_2021.era5_to_imd_ratio * 100)}%`} label="ERA5 annual rain as a share of IMD's (1991–2021)" />
        </div>
        <h4>Average monthly rainfall, IMD 1901–2021 (mm)</h4>
        <BarChart
          title="Average monthly rainfall in Mumbai, IMD 1901–2021"
          valueLabel="mm"
          bars={data.rainfall.climatology.map((m) => ({ label: MONTHS[m.month - 1], value: m.mean }))}
          formatValue={(v) => String(Math.round(v))}
        />
        <h4>Days with heavy rain (≥ 64.5 mm), ERA5 1991–2025</h4>
        <BarChart
          title="Heavy-rain days per year, ERA5"
          valueLabel="heavy-rain days"
          bars={data.rainfall.annual.map((a) => ({ label: String(a.year), value: a.heavy_days, tip: `${a.heavy_days} heavy-rain days · wettest day ${a.max_day_mm} mm` }))}
        />
      </Card>

      <Card f={byId.F4}>
        <p className="note">
          Each bar counts precisely located listed places by how low they sit compared with the rest of their own ward
          (0 = lowest tenth). If terrain carried no signal, bars would sit near the dashed line. Median percentile {f4.tpi_pct_in_ward.median};
          Wilcoxon p = {String((f4.tpi_pct_in_ward as Record<string, number | null>)["wilcoxon_p_vs_0.5"])} (n = {f4.n}).
        </p>
        <BarChart
          title="Listed places by relative-elevation percentile within their ward"
          valueLabel="places"
          bars={bins.map((b, i) => ({ label: `${i * 10}–${i * 10 + 10}%`, value: b }))}
          refLine={{ value: precise.length / 10, label: "no-signal level" }}
        />
      </Card>

      <Card f={byId.F5}>
        <div className="stats">
          <Stat value={`${f5.rows_without_pump_listed} / ${f5.bmc_rows}`} label="BMC-listed spots with no dewatering pump recorded" />
          <Stat value={String(f5.total_pumps_listed)} label="pumps listed across all BMC spots" />
          <Stat value={String(f5.rows_marked_planning_stage)} label="spots whose works are marked 'planning stage'" />
        </div>
      </Card>
    </div>
  );
}
