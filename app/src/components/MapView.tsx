import { useEffect, useRef, useState } from "react";
import maplibregl, { type GeoJSONSource, type Map as MLMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type { Location, Ward } from "../types";
import { CLASS_COLOR, isMapped } from "../lib/labels";

interface Props {
  locations: Location[];
  wards: Ward[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  showWards: boolean;
  dark: boolean;
}

const STYLE = (dark: boolean) => `https://tiles.openfreemap.org/styles/${dark ? "dark" : "positron"}`;
const MUMBAI_BOUNDS: [[number, number], [number, number]] = [[72.77, 18.88], [73.0, 19.28]];

function toGeoJSON(locs: Location[]): GeoJSON.FeatureCollection {
  return {
    type: "FeatureCollection",
    features: locs.filter(isMapped).map((l) => ({
      type: "Feature",
      id: l.location_id,
      properties: { id: l.location_id, precision: l.geocode_precision, n_sources: l.n_sources, name: l.name },
      geometry: { type: "Point", coordinates: [l.lon as number, l.lat as number] },
    })),
  };
}

export default function MapView({ locations, wards, selectedId, onSelect, showWards, dark }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<MLMap | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const latest = useRef({ locations, wards, selectedId, showWards, onSelect });
  latest.current = { locations, wards, selectedId, showWards, onSelect };

  // (Re)create the map when the theme changes - style URLs differ per theme.
  useEffect(() => {
    if (!el.current) return;
    setState("loading");
    const m = new maplibregl.Map({
      container: el.current,
      style: STYLE(dark),
      bounds: MUMBAI_BOUNDS,
      fitBoundsOptions: { padding: 12 },
      attributionControl: { compact: true },
      cooperativeGestures: false,
    });
    map.current = m;
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    // Fail only if the style never finishes loading; tiles may legitimately keep streaming.
    let styleLoaded = false;
    const failTimer = window.setTimeout(() => {
      if (!styleLoaded) setState("error");
    }, 20000);

    m.on("load", async () => {
      styleLoaded = true;
      window.clearTimeout(failTimer);
      try {
        const res = await fetch(`${import.meta.env.BASE_URL}data/wards.geojson`);
        const gj = (await res.json()) as GeoJSON.FeatureCollection;
        const cls = new Map(latest.current.wards.map((w) => [w.ward, w.incident_class]));
        gj.features.forEach((f) => {
          (f.properties as Record<string, unknown>).cls = cls.get((f.properties as { ward: string }).ward) ?? 0;
        });
        m.addSource("wards", { type: "geojson", data: gj });
        const colorExpr: maplibregl.ExpressionSpecification = [
          "match", ["get", "cls"],
          1, CLASS_COLOR[1], 2, CLASS_COLOR[2], 3, CLASS_COLOR[3], 4, CLASS_COLOR[4],
          5, CLASS_COLOR[5], 6, CLASS_COLOR[6], 7, CLASS_COLOR[7], "#999999",
        ];
        m.addLayer({ id: "ward-fill", type: "fill", source: "wards",
          paint: { "fill-color": colorExpr, "fill-opacity": dark ? 0.5 : 0.48 } });
        m.addLayer({ id: "ward-line", type: "line", source: "wards",
          paint: { "line-color": dark ? "#c3c2b7" : "#ffffff", "line-width": 1.2, "line-opacity": 0.8 } });
        m.addLayer({ id: "ward-label", type: "symbol", source: "wards",
          layout: { "text-field": ["get", "ward"], "text-size": 11, "text-font": ["Noto Sans Bold"] },
          paint: { "text-color": dark ? "#f0efec" : "#0b0b0b", "text-halo-color": dark ? "#1a1a19" : "#ffffff", "text-halo-width": 1.4 } });

        m.addSource("locs", { type: "geojson", data: toGeoJSON(latest.current.locations) });
        m.addLayer({ id: "loc-area", type: "circle", source: "locs", filter: ["==", ["get", "precision"], "area"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, 6, 15, 16],
            "circle-color": "rgba(235,104,52,0.10)",
            "circle-stroke-color": "#eb6834", "circle-stroke-width": 2,
          } });
        m.addLayer({ id: "loc-point", type: "circle", source: "locs", filter: ["!=", ["get", "precision"], "area"],
          paint: {
            "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, ["+", 4, ["get", "n_sources"]], 15, ["+", 8, ["*", 2, ["get", "n_sources"]]]],
            "circle-color": dark ? "#d95926" : "#eb6834",
            "circle-stroke-color": dark ? "#1a1a19" : "#ffffff", "circle-stroke-width": 2,
          } });
        m.addLayer({ id: "loc-selected", type: "circle", source: "locs", filter: ["==", ["get", "id"], ""],
          paint: { "circle-radius": 14, "circle-color": "rgba(0,0,0,0)",
            "circle-stroke-color": dark ? "#f0efec" : "#0b0b0b", "circle-stroke-width": 3 } });

        for (const layer of ["loc-point", "loc-area"]) {
          m.on("click", layer, (e) => {
            const id = e.features?.[0]?.properties?.id;
            if (id) latest.current.onSelect(String(id));
          });
          m.on("mouseenter", layer, () => (m.getCanvas().style.cursor = "pointer"));
          m.on("mouseleave", layer, () => (m.getCanvas().style.cursor = ""));
        }
        setState("ready");
      } catch {
        setState("error");
      }
    });
    m.on("error", (e) => {
      // tile hiccups are common; only fail hard if the style itself never loaded
      if (!m.isStyleLoaded() && String(e.error?.message ?? "").includes("style")) setState("error");
    });
    return () => {
      window.clearTimeout(failTimer);
      m.remove();
      map.current = null;
    };
  }, [dark]);

  useEffect(() => {
    const m = map.current;
    if (state !== "ready" || !m) return;
    (m.getSource("locs") as GeoJSONSource | undefined)?.setData(toGeoJSON(locations));
  }, [locations, state]);

  useEffect(() => {
    const m = map.current;
    if (state !== "ready" || !m) return;
    for (const id of ["ward-fill", "ward-line", "ward-label"]) {
      m.setLayoutProperty(id, "visibility", showWards ? "visible" : "none");
    }
  }, [showWards, state]);

  useEffect(() => {
    const m = map.current;
    if (state !== "ready" || !m) return;
    m.setFilter("loc-selected", ["==", ["get", "id"], selectedId ?? ""]);
    const loc = latest.current.locations.find((l) => l.location_id === selectedId);
    if (loc && isMapped(loc)) {
      m.easeTo({ center: [loc.lon as number, loc.lat as number], zoom: Math.max(m.getZoom(), 13), duration: 600 });
    }
  }, [selectedId, state]);

  return (
    <div className="map-wrap">
      <div ref={el} className="map" role="region" aria-label="Map of officially listed waterlogging locations in Mumbai. Use the list for a keyboard-accessible alternative." />
      {state === "loading" && <div className="map-overlay">Loading map…</div>}
      {state === "error" && (
        <div className="map-overlay map-overlay--error" role="alert">
          The basemap could not load (offline or tile service unavailable). All locations are still available in the list.
        </div>
      )}
    </div>
  );
}
