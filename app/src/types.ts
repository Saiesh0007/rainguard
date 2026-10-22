// Shapes of the static JSON produced by analysis/export_app_data.py.

export type Precision = "point" | "street" | "area" | "not_mappable";
export type Tier = "A" | "B" | "C";

export interface Location {
  location_id: string;
  name: string;
  detail: string | null;
  ward: string;
  sources: string;
  n_sources: number;
  record_ids: string;
  in_bmc_fpg_2026: boolean;
  in_best_annex_2026: boolean;
  in_mtp_2026: boolean;
  traffic_diversion: string | null;
  lat: number | null;
  lon: number | null;
  geocode_precision: Precision;
  geocode_osm_name: string | null;
  geocode_note: string | null;
  project_category: string | null;
  pumps: number | null;
  capacity_listed_m3hr: number | null;
  capacity_complete: boolean;
  elevation_m: number | null;
  tpi_m: number | null;
  tpi_pct_in_ward: number | null;
  neighbours_1km: number | null;
  incident_class: number;
  incidents_low: number;
  incidents_high: number;
  ward_burden: number;
  corroboration: number;
  low_lying: number | null;
  listing_density: number | null;
  components_available: number;
  priority_score: number;
  priority_rank: number;
  priority_tier: Tier;
  top20_frequency: number;
  rank_p10: number;
  rank_p90: number;
}

export interface Ward {
  ward: string;
  incident_class: number;
  incidents_low: number;
  incidents_high: number;
  population_2011: number;
  area_km2: number;
  density_per_km2: number;
  bmc_fpg2026_spots: number;
  best_annex_spots: number | null;
  mtp_diversion_rows: number;
  multi_source_locations: number;
  unique_locations: number;
  median_elevation_m: number;
  low_lying_share: number;
}

export interface Finding {
  id: string;
  title: string;
  evidence_type: string;
  numbers: Record<string, unknown>;
  method: string;
  period: string;
  sample: string;
  caveats: string[];
  figure: string | null;
}

export interface Source {
  id: string;
  name: string;
  publisher: string;
  url: string;
  accessed: string | null;
  kind: string;
  use: string;
  terms: string;
}

export interface ModelResult {
  features: string[];
  loo_mae_classes: number;
  loo_spearman: number | null;
  within_one_class: number;
  permutation_p_value?: number;
  mae_change_vs_B0: number;
}

export interface RainGuardData {
  generated_utc: string;
  sources: Source[];
  locations: Location[];
  wards: Ward[];
  findings: Finding[];
  rainfall: {
    summary: {
      imd: { jjas_share_of_annual: number; mean_annual_mm: number; years: number[] };
      era5: {
        years: number[];
        mean_heavy_days_per_year: number;
        "2005_07_26_mm": number;
        "2005_07_26_reference_mm": number;
      };
      era5_vs_imd_monthly_1991_2021: { era5_to_imd_ratio: number; pearson_r_all_months: number };
    };
    climatology: { month: number; mean: number; median: number }[];
    annual: { year: number; total_mm: number; max_day_mm: number; heavy_days: number; very_heavy_days: number; extreme_days: number }[];
  };
  evaluation: {
    ward_level: {
      n_wards: number;
      models: Record<string, ModelResult>;
      spearman_population_vs_class: { rho: number; p: number };
    };
    location_terrain_case_control: Record<
      string,
      { n: number; tpi_pct_in_ward: { median: number; wilcoxon_p_vs_0_5?: number } & Record<string, number | null> }
    >;
  };
  sensitivity: {
    n_locations: number;
    n_weight_draws: number;
    default_weights: Weights;
    spearman_default_vs_random_weights: { median: number; p5: number };
    top20_jaccard_default_vs_random_weights: { median: number; p5: number };
    ablation_drop_one_component: Record<string, { spearman_vs_default: number; top20_jaccard: number }>;
  };
  verification: Record<string, Record<string, unknown>>;
  cleaning: {
    unique_locations: number;
    by_n_sources: Record<string, number>;
    by_precision: Record<string, number>;
  };
}

export interface Weights {
  ward_burden: number;
  corroboration: number;
  low_lying: number;
  listing_density: number;
}
