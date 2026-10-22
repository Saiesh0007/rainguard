// Live 3-day rain outlook from the free Open-Meteo Forecast API (no key, CC BY 4.0).
// This is a THIRD-PARTY MODEL FORECAST for one point in Mumbai - not a RainGuard prediction.

export const FORECAST_URL =
  "https://api.open-meteo.com/v1/forecast?latitude=19.07&longitude=72.87" +
  "&daily=precipitation_sum,precipitation_probability_max&timezone=Asia%2FKolkata&forecast_days=3";

const CACHE_KEY = "rainguard.forecast.v1";
export const STALE_AFTER_MS = 3 * 60 * 60 * 1000;

export interface ForecastDay {
  date: string;
  rainMm: number | null;
  probabilityPct: number | null;
}

export interface Forecast {
  fetchedAt: number;
  days: ForecastDay[];
}

export type ForecastState =
  | { status: "loading" }
  | { status: "ok"; forecast: Forecast; stale: boolean }
  | { status: "error"; message: string; cached: Forecast | null };

/** IMD 24-hour rainfall categories (mm). */
export function imdCategory(mm: number | null): { label: string; level: 0 | 1 | 2 | 3 | 4 | 5 } {
  if (mm === null) return { label: "No data", level: 0 };
  if (mm < 2.5) return { label: "Little or no rain", level: 0 };
  if (mm < 15.6) return { label: "Light to moderate rain", level: 1 };
  if (mm < 64.5) return { label: "Moderate to rather heavy rain", level: 2 };
  if (mm < 115.6) return { label: "Heavy rain", level: 3 };
  if (mm < 204.5) return { label: "Very heavy rain", level: 4 };
  return { label: "Extremely heavy rain", level: 5 };
}

/** Index into outlook.forecast_track_record.by_forecast_amount (analysis/predict.py FC_BINS: <15.6, <35, <64.5, more). */
export function trackBand(mm: number | null): number | null {
  if (mm === null) return null;
  if (mm < 15.6) return 0;
  if (mm < 35) return 1;
  if (mm < 64.5) return 2;
  return 3;
}

export function parseForecast(json: unknown, now = Date.now()): Forecast {
  const d = (json as { daily?: Record<string, unknown[]> }).daily;
  if (!d || !Array.isArray(d.time) || !Array.isArray(d.precipitation_sum)) {
    throw new Error("Unexpected forecast format");
  }
  const prob = Array.isArray(d.precipitation_probability_max) ? d.precipitation_probability_max : [];
  return {
    fetchedAt: now,
    days: d.time.map((t, i) => ({
      date: String(t),
      rainMm: typeof d.precipitation_sum[i] === "number" ? (d.precipitation_sum[i] as number) : null,
      probabilityPct: typeof prob[i] === "number" ? (prob[i] as number) : null,
    })),
  };
}

function readCache(): Forecast | null {
  try {
    const raw = localStorage.getItem(CACHE_KEY);
    return raw ? (JSON.parse(raw) as Forecast) : null;
  } catch {
    return null;
  }
}

function writeCache(f: Forecast) {
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(f));
  } catch {
    /* storage unavailable - the app works without it */
  }
}

export async function loadForecast(fetcher: typeof fetch = fetch, now = Date.now()): Promise<ForecastState> {
  const cached = readCache();
  try {
    const res = await fetcher(FORECAST_URL);
    if (!res.ok) throw new Error(`Forecast service returned ${res.status}`);
    const f = parseForecast(await res.json(), now);
    writeCache(f);
    return { status: "ok", forecast: f, stale: false };
  } catch (e) {
    if (cached) return { status: "ok", forecast: cached, stale: now - cached.fetchedAt > STALE_AFTER_MS };
    return { status: "error", message: e instanceof Error ? e.message : String(e), cached: null };
  }
}
