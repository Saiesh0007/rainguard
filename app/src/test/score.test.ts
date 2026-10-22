import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { priorityScore, rankScores, rescore, tierFor } from "../lib/score";
import type { RainGuardData } from "../types";

const data: RainGuardData = JSON.parse(
  readFileSync(resolve(__dirname, "../../public/data/rainguard.json"), "utf8"),
);

describe("client-side score matches analysis/score.py", () => {
  const w = data.sensitivity.default_weights;
  it("reproduces every exported priority score", () => {
    for (const l of data.locations) {
      // exported scores are rounded to 0.1
      expect(Math.abs(priorityScore(l, w) - l.priority_score)).toBeLessThanOrEqual(0.0501);
    }
  });
  it("reproduces exported ranks and tiers", () => {
    const out = rescore(data.locations, w);
    for (const r of out) {
      expect(r.rank).toBe(r.loc.priority_rank);
      expect(r.tier).toBe(r.loc.priority_tier);
    }
  });
});

describe("scoring rules", () => {
  const base = data.locations[0];
  it("skips missing components instead of treating them as zero", () => {
    const loc = { ...base, ward_burden: 1, ward_excess: 1, corroboration: 1, low_lying: null, listing_density: 1 };
    expect(priorityScore(loc, { ward_burden: 1, ward_excess: 1, corroboration: 1, low_lying: 1, listing_density: 1 })).toBe(100);
  });
  it("returns 0 when every weight is zero", () => {
    expect(priorityScore(base, { ward_burden: 0, ward_excess: 0, corroboration: 0, low_lying: 0, listing_density: 0 })).toBe(0);
  });
  it("gives tied scores the same (lowest) rank", () => {
    expect(rankScores([10, 50, 50, 20])).toEqual([4, 1, 1, 3]);
  });
  it("assigns tiers by rank share", () => {
    expect(tierFor(1, 100)).toBe("A");
    expect(tierFor(20, 100)).toBe("A");
    expect(tierFor(21, 100)).toBe("B");
    expect(tierFor(51, 100)).toBe("C");
  });
});
