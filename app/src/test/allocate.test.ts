import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { diagnosisOf, inspectionPlan } from "../lib/allocate";
import { rescore } from "../lib/score";
import type { Location, RainGuardData } from "../types";

const data: RainGuardData = JSON.parse(
  readFileSync(resolve(__dirname, "../../public/data/rainguard.json"), "utf8"),
);

describe("client-side plan matches analysis/allocate.py", () => {
  it("reproduces the exported default plan", () => {
    const a = data.allocation;
    const plan = inspectionPlan(rescore(data.locations, data.sensitivity.default_weights), a.k, a.cap_per_ward);
    expect(plan.map((r) => r.loc.location_id)).toEqual(a.default_plan);
  });
});

describe("plan rules", () => {
  const mk = (id: string, ward: string, rank: number) => ({ loc: { location_id: id, ward } as Location, rank });
  it("never puts more than the cap in one ward", () => {
    const ranked = [mk("a", "K/W", 1), mk("b", "K/W", 2), mk("c", "K/W", 3), mk("d", "L", 4)];
    expect(inspectionPlan(ranked, 3, 2).map((r) => r.loc.location_id)).toEqual(["a", "b", "d"]);
  });
  it("breaks rank ties by location id", () => {
    expect(inspectionPlan([mk("z", "A", 1), mk("b", "B", 1)], 1, 3)[0].loc.location_id).toBe("b");
  });
  it("returns fewer than K when the cap runs out", () => {
    expect(inspectionPlan([mk("a", "A", 1), mk("b", "A", 2)], 5, 1)).toHaveLength(1);
  });
});

describe("diagnosis labels", () => {
  it("every label used on a place is defined, and counts match the summary", () => {
    const counts: Record<string, number> = {};
    for (const l of data.locations) for (const d of diagnosisOf(l)) counts[d] = (counts[d] ?? 0) + 1;
    for (const [id, lab] of Object.entries(data.diagnosis.labels)) expect(counts[id] ?? 0).toBe(lab.n);
    expect(Object.keys(counts).every((k) => k in data.diagnosis.labels)).toBe(true);
  });
  it("pump_gap only on BMC-listed places with no pump", () => {
    for (const l of data.locations.filter((x) => diagnosisOf(x).includes("pump_gap"))) {
      expect(l.in_bmc_fpg_2026).toBe(true);
      expect(l.pumps).toBeNull();
    }
  });
});
