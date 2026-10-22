// Client-side re-implementation of analysis/score.py so civic users can change weights.
// tests/score.test.ts checks it reproduces the exported Python scores exactly.
import type { Location, Weights } from "../types";

export const COMPONENTS = ["ward_burden", "ward_excess", "corroboration", "low_lying", "listing_density"] as const;
export type Component = (typeof COMPONENTS)[number];

export const COMPONENT_LABEL: Record<Component, string> = {
  ward_burden: "Ward incident history (mostly follows population)",
  ward_excess: "Ward incidents beyond what population explains",
  corroboration: "Named by several official lists",
  low_lying: "Lower than surroundings (unvalidated)",
  listing_density: "Other listed places within 1 km",
};

/** Weighted mean of the available components, 0-100. Missing components are skipped, never imputed. */
export function priorityScore(loc: Location, w: Weights): number {
  let num = 0;
  let den = 0;
  for (const c of COMPONENTS) {
    const v = loc[c];
    if (v === null || v === undefined) continue;
    num += v * w[c];
    den += w[c];
  }
  return den > 0 ? (100 * num) / den : 0;
}

/** Rank with ties sharing the lowest rank (pandas rank(method="min", ascending=False)). */
export function rankScores(scores: number[]): number[] {
  // round first so floating-point noise never splits genuine ties (analysis/score.py does the same)
  const r = scores.map((s) => Math.round(s * 1e6) / 1e6);
  return r.map((s) => 1 + r.filter((o) => o > s).length);
}

export function tierFor(rank: number, n: number): "A" | "B" | "C" {
  if (rank <= Math.round(0.2 * n)) return "A";
  if (rank <= Math.round(0.5 * n)) return "B";
  return "C";
}

export function rescore(locs: Location[], w: Weights) {
  const scores = locs.map((l) => priorityScore(l, w));
  const ranks = rankScores(scores);
  return locs.map((l, i) => ({ loc: l, score: scores[i], rank: ranks[i], tier: tierFor(ranks[i], locs.length) }));
}
