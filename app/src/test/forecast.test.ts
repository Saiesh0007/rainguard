import { beforeEach, describe, expect, it } from "vitest";
import { STALE_AFTER_MS, imdCategory, loadForecast, parseForecast } from "../lib/forecast";

const sample = {
  daily: { time: ["2026-07-01", "2026-07-02", "2026-07-03"], precipitation_sum: [0, 80.2, 210], precipitation_probability_max: [5, 90, 95] },
};

describe("IMD categories", () => {
  it.each([
    [0, 0], [2.4, 0], [2.5, 1], [15.5, 1], [15.6, 2], [64.4, 2], [64.5, 3], [115.5, 3], [115.6, 4], [204.4, 4], [204.5, 5],
  ])("%f mm -> level %i", (mm, level) => {
    expect(imdCategory(mm).level).toBe(level);
  });
  it("treats missing values as no data", () => {
    expect(imdCategory(null).label).toBe("No data");
  });
});

describe("parseForecast", () => {
  it("reads the Open-Meteo daily shape", () => {
    const f = parseForecast(sample, 123);
    expect(f.fetchedAt).toBe(123);
    expect(f.days).toHaveLength(3);
    expect(f.days[1]).toEqual({ date: "2026-07-02", rainMm: 80.2, probabilityPct: 90 });
  });
  it("rejects unexpected payloads", () => {
    expect(() => parseForecast({ hourly: {} })).toThrow();
  });
});

describe("loadForecast states", () => {
  beforeEach(() => localStorage.clear());
  const ok = (async () => new Response(JSON.stringify(sample))) as unknown as typeof fetch;
  const fail = (async () => { throw new Error("offline"); }) as unknown as typeof fetch;

  it("returns fresh data on success", async () => {
    const s = await loadForecast(ok, 1000);
    expect(s.status).toBe("ok");
    if (s.status === "ok") expect(s.stale).toBe(false);
  });
  it("returns an error (not invented data) when offline with no cache", async () => {
    const s = await loadForecast(fail, 1000);
    expect(s.status).toBe("error");
  });
  it("falls back to an old cache and marks it stale", async () => {
    await loadForecast(ok, 1000);
    const s = await loadForecast(fail, 1000 + STALE_AFTER_MS + 1);
    expect(s.status).toBe("ok");
    if (s.status === "ok") expect(s.stale).toBe(true);
  });
});
