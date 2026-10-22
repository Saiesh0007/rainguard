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
  incident_excess: number;
  ward_burden: number;
  ward_excess: number;
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
  plan_frequency: number;
  /** "|"-separated DiagnosisId values; "" when no label applies */
  diagnosis: string;
}

export type DiagnosisId = "pump_gap" | "list_gap" | "corroborated" | "traffic_critical" | "needs_location";

export interface DiagnosisLabel {
  cause: string;
  title: string;
  rule: string;
  check: string;
  n: number;
}

export interface Allocation {
  k: number;
  cap_per_ward: number;
  n_weight_draws: number;
  rule: string;
  default_plan: string[];
  wards_in_default_plan: number;
  wards_in_uncapped_top_k: number;
  plan_jaccard_vs_default: { median: number; p5: number };
  stable_core_threshold: number;
  stable_core: string[];
}

export interface OutlookScore {
  brier: number;
  brier_skill_vs_climatology: number;
  auc: number;
  brier_skill_95ci?: [number, number];
}

export interface Outlook {
  heavy_mm: number;
  observed_model: {
    target: string;
    season: string;
    split_years: Record<"train" | "validate" | "test", [number, number]>;
    n_days: Record<string, number>;
    heavy_share: Record<string, number>;
    validation: Record<string, OutlookScore>;
    chosen_on_validation: string;
    test: Record<string, OutlookScore>;
    test_reliability_chosen: { bin: string; n: number; mean_predicted: number; observed_share: number }[];
    persistence_1971_2016: {
      p_heavy_tomorrow_if_heavy_today: number;
      p_heavy_tomorrow_if_not_heavy_today: number;
      n_heavy_today: number;
    };
  };
  forecast_track_record: {
    source: string;
    period: string;
    years: number[];
    n_days: number;
    observed_heavy_days: number;
    by_forecast_amount: { forecast: string; n_days: number; heavy_days: number; heavy_share: number | null }[];
    forecast_ge_64_5mm: {
      hits: number; misses: number; false_alarms: number;
      probability_of_detection: number | null; false_alarm_ratio: number | null;
    };
    correlation_fc_vs_observed: number;
    caveat: string;
  };
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
  incident_class_expected_from_pop: number;
  incident_excess: number;
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
    locations_in_top20_in_at_least_80pct_of_draws: number;
    population_adjusted_alternative: { weights: Weights; spearman_vs_default: number; top20_jaccard_vs_default: number };
  };
  diagnosis: { n_locations: number; labels: Record<DiagnosisId, DiagnosisLabel>; with_no_label: number };
  allocation: Allocation;
  outlook: Outlook;
  verification: Record<string, Record<string, unknown>>;
  cleaning: {
    unique_locations: number;
    by_n_sources: Record<string, number>;
    by_precision: Record<string, number>;
  };
}

export interface Weights {
  ward_burden: number;
  ward_excess: number;
  corroboration: number;
  low_lying: number;
  listing_density: number;
}
