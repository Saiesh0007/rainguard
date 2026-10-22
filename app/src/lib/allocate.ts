// Client-side re-implementation of analysis/allocate.py so planners can change K, the ward cap and weights.
// tests/allocate.test.ts checks it reproduces the exported default plan exactly.
import type { DiagnosisId, Location } from "../types";

export interface Ranked {
  loc: Location;
  rank: number;
}

/** Walk down the priority order (ties broken by location_id) and take each place unless its ward already has `cap`. */
export function inspectionPlan<T extends Ranked>(ranked: T[], k: number, cap: number): T[] {
  const order = [...ranked].sort((a, b) => a.rank - b.rank || (a.loc.location_id < b.loc.location_id ? -1 : 1));
  const perWard = new Map<string, number>();
  const taken: T[] = [];
  for (const r of order) {
    if (taken.length >= k) break;
    const n = perWard.get(r.loc.ward) ?? 0;
    if (n >= cap) continue;
    taken.push(r);
    perWard.set(r.loc.ward, n + 1);
  }
  return taken;
}

export function diagnosisOf(l: Location): DiagnosisId[] {
  return l.diagnosis ? (l.diagnosis.split("|") as DiagnosisId[]) : [];
}
