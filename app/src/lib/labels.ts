// Plain-language labels shared across views. The five evidence kinds follow Project.md section 7.
import type { Location, Precision } from "../types";

export type EvidenceKind = "observed" | "historical" | "estimated" | "forecast" | "unknown";

export const EVIDENCE: Record<EvidenceKind, { label: string; help: string }> = {
  observed: { label: "Observed", help: "Directly measured data, e.g. IMD rainfall." },
  historical: { label: "Historical", help: "Recorded in the past by an official source." },
  estimated: { label: "Estimated", help: "Output of a model or our transparent rules." },
  forecast: { label: "Forecast", help: "A third-party model's estimate of the future." },
  unknown: { label: "Unknown", help: "Not available or not enough evidence." },
};

export const SOURCE_LABEL: Record<string, string> = {
  BMC_FPG_2026: "BMC Flood Preparedness Guidelines 2026",
  BEST_ANNEX_IX_2026: "BEST flood-prone areas list 2026",
  MTP_DIVERSIONS_2026: "Mumbai Traffic Police diversion plan",
};

export const SOURCE_SHORT: Record<string, string> = {
  BMC_FPG_2026: "BMC",
  BEST_ANNEX_IX_2026: "BEST",
  MTP_DIVERSIONS_2026: "Traffic police",
};

export const PRECISION_LABEL: Record<Precision, string> = {
  point: "Exact place found",
  street: "Somewhere along this road",
  area: "Neighbourhood only (approximate)",
  not_mappable: "Could not be placed on the map",
};

export const INCIDENT_CLASS_RANGE: Record<number, string> = {
  1: "0–115", 2: "116–130", 3: "131–212", 4: "213–270", 5: "271–316", 6: "317–466", 7: "467–800",
};

/** Ordinal blue ramp (dataviz reference palette, steps 250-700) for incident classes 1-7. */
export const CLASS_COLOR: Record<number, string> = {
  1: "#86b6ef", 2: "#6da7ec", 3: "#3987e5", 4: "#2a78d6", 5: "#1c5cab", 6: "#184f95", 7: "#0d366b",
};

export const TIER_TEXT: Record<string, string> = {
  A: "Inspect first",
  B: "Inspect next",
  C: "Routine check",
};

export function sourcesOf(l: Location): string[] {
  return l.sources.split("|");
}

export function isMapped(l: Location): boolean {
  return l.lat !== null && l.lon !== null && l.geocode_precision !== "not_mappable";
}

export function formatInt(n: number): string {
  return new Intl.NumberFormat("en-IN").format(Math.round(n));
}
