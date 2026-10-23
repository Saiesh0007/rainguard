// Landing page: the same story as docs/demo_script.md, told with numbers read from rainguard.json.
import type { RainGuardData } from "../types";
import type { ForecastState } from "../lib/forecast";
import { diagnosisOf } from "../lib/allocate";
import ForecastCard from "./ForecastCard";
import DiagnosisChips from "./DiagnosisChips";
import EvidenceChip from "./EvidenceChip";
import Icon from "./Icon";
import { EVIDENCE, type EvidenceKind } from "../lib/labels";

type Target = "map" | "insights" | "civic" | "method";

interface Props {
  data: RainGuardData;
  forecast: ForecastState;
  onGo: (t: Target) => void;
  onOpen: (id: string) => void;
}

const pct = (x: number) => `${Math.round(x * 100)}%`;

export default function Home({ data, forecast, onGo, onOpen }: Props) {
  const n = data.locations.length;
  const multi = data.locations.filter((l) => l.n_sources >= 2).length;
  const labels = data.diagnosis.labels;
  const pumpGap = labels.pump_gap.n;
  const bmcListed = data.locations.filter((l) => l.in_bmc_fpg_2026).length;
  const f2 = data.findings.find((f) => f.id === "F2")?.numbers as { best_rows_per_ward_where_bmc_lists_nil?: Record<string, number> } | undefined;
  const nilWards = Object.entries(f2?.best_rows_per_ward_where_bmc_lists_nil ?? {});
  const nilBest = nilWards.reduce((s, [, v]) => s + v, 0);
  const rho = data.evaluation.ward_level.spearman_population_vs_class.rho;
  const o = data.outlook.observed_model;
  const chosen = o.test[o.chosen_on_validation];
  const per = o.persistence_1971_2016;
  const fc = data.outlook.forecast_track_record.forecast_ge_64_5mm;
  const years = o.split_years.test[1] - o.split_years.train[0] + 1;
  const alloc = data.allocation;
  const byId = new Map(data.locations.map((l) => [l.location_id, l]));
  const planTop = alloc.default_plan.slice(0, 4).map((id) => byId.get(id)).filter((l) => l !== undefined);
  const example = data.locations.find((l) => /hindmata/i.test(l.name));
  const areaOnly = data.cleaning.by_precision.area ?? 0;

  return (
    <div className="home">
      {/* 0:00 - hook and user */}
      <section className="hero">
        <p className="eyebrow">Mumbai monsoon · HackAMatch 1.0 · CityPulse</p>
        <h2 className="hero__title">
          {n} places waterlog in Mumbai's monsoon. <span className="hero__accent">Only {multi} are on more than one official list.</span>
        </h2>
        <p className="hero__lead">
          BMC, BEST and the Mumbai Traffic Police each publish their own list. RainGuard brings them together for the
          ward engineer who has to decide: <strong>where do my teams inspect first, what do they check, and is tomorrow likely to be a heavy-rain day?</strong>
        </p>
        <div className="hero__cta">
          <button className="btn btn--lg" onClick={() => onGo("civic")}><Icon name="shield" size={18} />Open this week's plan</button>
          <button className="btn btn--outline btn--lg" onClick={() => onGo("map")}><Icon name="map" size={18} />Explore the map</button>
        </div>
        <ul className="hero__stats">
          <li><strong>{n}</strong><span>official flood-prone places</span></li>
          <li><strong>{multi}</strong><span>named by 2 or more lists</span></li>
          <li><strong>{pumpGap} / {bmcListed}</strong><span>BMC-listed places with no pump recorded</span></li>
          <li><strong>{pct(per.p_heavy_tomorrow_if_heavy_today)}</strong><span>chance a heavy-rain day is followed by another</span></li>
        </ul>
      </section>

      {/* the three questions */}
      <section className="home__band">
        <h3 className="home__h">Three questions, one screen each</h3>
        <div className="qgrid">
          <button className="qcard" onClick={() => onGo("civic")}>
            <span className="qcard__n">1</span>
            <span className="qcard__q">Where should my teams go first?</span>
            <span className="qcard__a">A weekly plan of {alloc.k} places, at most {alloc.cap_per_ward} per ward, covering {alloc.wards_in_default_plan} wards instead of {alloc.wards_in_uncapped_top_k}.</span>
            <span className="qcard__go">Plan <Icon name="chevron" size={16} /></span>
          </button>
          <button className="qcard" onClick={() => onGo("civic")}>
            <span className="qcard__n">2</span>
            <span className="qcard__q">What should they check there?</span>
            <span className="qcard__a">Rule-based labels read from the official lists: no pump recorded, missing from BMC's list, traffic diversion, exact spot unknown.</span>
            <span className="qcard__go">Plan <Icon name="chevron" size={16} /></span>
          </button>
          <button className="qcard" onClick={() => onGo("method")}>
            <span className="qcard__n">3</span>
            <span className="qcard__q">Is tomorrow a heavy-rain day?</span>
            <span className="qcard__a">A city-wide outlook tested on {o.split_years.test[0]}–{o.split_years.test[1]}, plus the live forecast's measured track record.</span>
            <span className="qcard__go">Method <Icon name="chevron" size={16} /></span>
          </button>
        </div>
      </section>

      {/* 0:25 - data, and what it cannot do */}
      <section className="home__band">
        <h3 className="home__h">What the data can and cannot tell you</h3>
        <div className="cando">
          <div className="card cando__col">
            <p className="cando__title cando__title--yes"><Icon name="check" size={18} />Can</p>
            <ul>
              <li>Name {n} places three official agencies expect to waterlog, with where each list agrees.</li>
              <li>Say what to check at each place, straight from the lists.</li>
              <li>Predict a city-wide heavy-rain day from {years} years of observed IMD daily rainfall, tested on years it never saw.</li>
            </ul>
          </div>
          <div className="card cando__col">
            <p className="cando__title cando__title--no"><Icon name="alert" size={18} />Cannot</p>
            <ul>
              <li>Forecast flooding on a particular street: no free source records when and where waterlogging happened.</li>
              <li>See rain differences between neighbourhoods: free rainfall is a 25 km grid.</li>
              <li>Tell you a road is safe. A place missing from every list may still flood.</li>
            </ul>
          </div>
        </div>
        <p className="fine">
          {data.sources.length} free public sources, each with its licence and access date. No API keys, no paid services.{" "}
          <button className="link-btn" onClick={() => onGo("method")}>See every source</button>
        </p>
      </section>

      {/* 1:05 - findings */}
      <section className="home__band">
        <h3 className="home__h">Three findings that shape the product</h3>
        <div className="fgrid">
          <article className="card fcard">
            <p className="eyebrow">F2 · <EvidenceChip kind="historical" /></p>
            <p className="fcard__big">{multi} of {n}</p>
            <p>The lists disagree. BMC's 2026 list says wards {nilWards.map(([w]) => w).join(", ")} have no waterlogging spots; BEST lists {nilBest} places there.</p>
          </article>
          <article className="card fcard">
            <p className="eyebrow">F1 · <EvidenceChip kind="historical" /></p>
            <p className="fcard__big">ρ = {rho}</p>
            <p>Recorded ward incidents mostly follow population, so ward history is shown as context, not as a hazard map.</p>
          </article>
          <article className="card fcard">
            <p className="eyebrow">F6 · <EvidenceChip kind="observed" /></p>
            <p className="fcard__big">{pct(per.p_heavy_tomorrow_if_heavy_today)} vs {pct(per.p_heavy_tomorrow_if_not_heavy_today)}</p>
            <p>Heavy rain clusters: after a heavy-rain day the next is heavy {pct(per.p_heavy_tomorrow_if_heavy_today)} of the time, against {pct(per.p_heavy_tomorrow_if_not_heavy_today)} otherwise.</p>
          </article>
        </div>
        <button className="btn btn--ghost" onClick={() => onGo("insights")}>All six findings <Icon name="chevron" size={16} /></button>
      </section>

      {/* 1:50 - the prediction and how it was tested */}
      <section className="home__band home__split">
        <div>
          <h3 className="home__h">A prediction we could actually test</h3>
          <p>
            Each morning at 08:30, from the rain just measured, RainGuard gives the chance that the next 24 hours are a heavy-rain day
            (IMD ≥ {data.outlook.heavy_mm} mm). It is a rain outlook for the whole city, not a flood forecast for a street.
          </p>
          <ol className="timeline" aria-label="Chronological split">
            <li style={{ flexGrow: o.split_years.train[1] - o.split_years.train[0] + 1 }}><span>Train</span>{o.split_years.train[0]}–{o.split_years.train[1]}</li>
            <li style={{ flexGrow: o.split_years.validate[1] - o.split_years.validate[0] + 1 }}><span>Choose</span>{o.split_years.validate[0]}–{String(o.split_years.validate[1]).slice(2)}</li>
            <li className="is-test" style={{ flexGrow: o.split_years.test[1] - o.split_years.test[0] + 1 }}><span>Test once</span>{o.split_years.test[0]}–{String(o.split_years.test[1]).slice(2)}</li>
          </ol>
          <ul className="metrics">
            <li><strong>{chosen.brier_skill_vs_climatology.toFixed(2)}</strong><span>Brier skill vs the monthly baseline{chosen.brier_skill_95ci ? ` (95%: ${chosen.brier_skill_95ci[0].toFixed(2)}–${chosen.brier_skill_95ci[1].toFixed(2)})` : ""}</span></li>
            <li><strong>{chosen.auc.toFixed(2)}</strong><span>ROC AUC on the test years</span></li>
            <li><strong>{fc.hits} of {fc.hits + fc.misses}</strong><span>heavy days the live forecast's own "heavy" call caught, so we quote its track record instead</span></li>
          </ul>
        </div>
        <ForecastCard state={forecast} track={data.outlook.forecast_track_record} />
      </section>

      {/* 2:30 - the weekly plan */}
      <section className="home__band">
        <h3 className="home__h">This week's plan, with what to check</h3>
        <p className="muted">The first {planTop.length} of {alloc.k} places in the default plan. Change the number of places, the ward cap and the weights in the Plan tab.</p>
        <ol className="planlist">
          {planTop.map((l, i) => {
            const dx = diagnosisOf(l);
            return (
              <li key={l.location_id}>
                <span className="planlist__n">{i + 1}</span>
                <div>
                  <button className="link-btn planlist__name" onClick={() => onOpen(l.location_id)}>{l.name}</button>
                  <span className="fine"> · ward {l.ward}</span>
                  <div><DiagnosisChips ids={dx} labels={labels} /></div>
                  <p className="fine">{dx.length ? labels[dx[0]].check : "Routine pre-monsoon check"}.</p>
                </div>
              </li>
            );
          })}
        </ol>
        <button className="btn" onClick={() => onGo("civic")}><Icon name="shield" size={16} />Open the full plan</button>
      </section>

      {/* 3:35 - one place, end to end */}
      <section className="home__band">
        <h3 className="home__h">Every place explains itself</h3>
        <p>Each block in a place's panel says what kind of evidence it is:</p>
        <ul className="evlist">
          {(Object.keys(EVIDENCE) as EvidenceKind[]).map((k) => <li key={k}><EvidenceChip kind={k} /> <span>{EVIDENCE[k].help}</span></li>)}
        </ul>
        {example && (
          <button className="btn btn--outline" onClick={() => onOpen(example.location_id)}>
            <Icon name="pin" size={16} />See {example.name}, ward {example.ward}
          </button>
        )}
      </section>

      {/* 4:20 - limits */}
      <section className="home__band home__limits">
        <h3 className="home__h">What could make us wrong</h3>
        <ul>
          <li>The lists are undated and incomplete; they say where water is expected, not when it happened.</li>
          <li>{areaOnly} places are only known to the neighbourhood.</li>
          <li>The outlook predicts rain, not water on the road, and only for the whole city.</li>
          <li>We looked for tide records and official disruption dates, and found none we could use.</li>
        </ul>
        <p>
          With BMC's dated complaint records and open rain-gauge data, this could become a street-level early warning. Until then,
          RainGuard gives ward teams a ranked, explained plan, and says exactly how sure it is.
        </p>
        <div className="hero__cta">
          <button className="btn" onClick={() => onGo("method")}><Icon name="info" size={16} />Read the method and limits</button>
          <a className="btn btn--outline" href="tel:1916"><Icon name="phone" size={16} />BMC helpline 1916</a>
        </div>
      </section>
    </div>
  );
}
