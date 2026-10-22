// Integrity checks on the exported data the UI depends on.
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import type { RainGuardData } from "../types";

const data: RainGuardData = JSON.parse(
  readFileSync(resolve(__dirname, "../../public/data/rainguard.json"), "utf8"),
);
const WARDS = new Set(["A", "B", "C", "D", "E", "F/N", "F/S", "G/N", "G/S", "H/E", "H/W", "K/E", "K/W", "L",
  "M/E", "M/W", "N", "P/N", "P/S", "R/C", "R/N", "R/S", "S", "T"]);

describe("exported data", () => {
  it("has all 24 legacy wards with an incident class 1-7", () => {
    expect(data.wards).toHaveLength(24);
    for (const w of data.wards) {
      expect(WARDS.has(w.ward)).toBe(true);
      expect(w.incident_class).toBeGreaterThanOrEqual(1);
      expect(w.incident_class).toBeLessThanOrEqual(7);
    }
  });
  it("gives every location a known ward, a source and a valid precision", () => {
    for (const l of data.locations) {
      expect(WARDS.has(l.ward)).toBe(true);
      expect(l.n_sources).toBeGreaterThanOrEqual(1);
      expect(["point", "street", "area", "not_mappable"]).toContain(l.geocode_precision);
    }
  });
  it("only places coordinates inside Greater Mumbai, and none for unmappable rows", () => {
    for (const l of data.locations) {
      if (l.geocode_precision === "not_mappable") {
        expect(l.lat).toBeNull();
        continue;
      }
      expect(l.lat).toBeGreaterThan(18.85);
      expect(l.lat).toBeLessThan(19.3);
      expect(l.lon).toBeGreaterThan(72.75);
      expect(l.lon).toBeLessThan(73.05);
    }
  });
  it("never assesses terrain for approximate locations", () => {
    for (const l of data.locations) {
      if (l.geocode_precision === "area" || l.geocode_precision === "not_mappable") expect(l.low_lying).toBeNull();
    }
  });
  it("contains no phone numbers", () => {
    expect(JSON.stringify(data.locations)).not.toMatch(/\b\d{10}\b/);
  });
  it("has at least three findings, each with method, period, sample and caveats", () => {
    expect(data.findings.length).toBeGreaterThanOrEqual(3);
    for (const f of data.findings) {
      expect(f.method && f.period && f.sample).toBeTruthy();
      expect(f.caveats.length).toBeGreaterThan(0);
    }
  });
  it("does not present the priority score as a probability", () => {
    expect(JSON.stringify(data.findings)).not.toMatch(/probability of flooding/i);
  });
});
