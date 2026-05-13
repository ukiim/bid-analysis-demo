export interface AnnouncementMeta {
  id: string;
  title: string;
  type?: string;
  org?: string;
  area?: string | null;
  budget?: number | null;
  parent_org?: string | null;
  category?: string;
  ordering_org_name?: string;
  base_amount?: number | null;
}

export interface FrequencyBin {
  rate: number;
  count: number;
  first_place_count: number;
}

export interface FrequencyPeak {
  rate: number;
  range_start: number;
  range_end: number;
  count: number;
}

export interface PredictionCandidate {
  rate: number;
  frequency: number;
  first_place_count: number;
  first_place_ratio: number;
  score: number;
  bid_amount: number;
  is_recommended: boolean;
  rank: number;
}

export interface FrequencyStats {
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
}

export interface AnalysisFrequencyResponse {
  bins: FrequencyBin[];
  peaks: FrequencyPeak[];
  stats: FrequencyStats;
  data_count: number;
  first_place_total: number;
  bin_size?: number;          // KBID 동등성: 매트릭스 정밀도 (0.01 등)
  category_filter?: string;   // 동일공종 풀 설정
  org_scope?: string;         // 동일발주처 풀 설정
  prediction_candidates: PredictionCandidate[];
  announcement: AnnouncementMeta;
}

export interface BucketItem {
  rate: number;
  score: number;
  side: "+" | "-" | "0";
  distance: number;
  range_start: number;
  range_end: number;
  rank: number;
  mode: "A" | "B" | "C";
}

export interface AnalysisRateBucketsResponse {
  announcement: AnnouncementMeta;
  params: {
    period_months: number;
    category_filter: string;
    detail_rule: string;
  };
  data_count: number;
  histogram: { rate: number; count: number }[];
  buckets: { A: BucketItem[]; B: BucketItem[]; C: BucketItem[] };
  detail_rate: number | null;
  predicted_bid_amount: number | null;
}

export interface CompanyRateRecord {
  // 백엔드 실제 응답 (analysis.py company-rates):
  // { company, rate, amount, ranking, is_first_place }
  company: string;
  rate: number;
  amount: number | null;
  ranking: number | null;
  is_first_place: boolean;
  // 레거시 호환
  company_name?: string;
  count?: number;
  first_place_count?: number;
}

export interface GapItem {
  start: number;
  end: number;
  size: number;
  midpoint: number;
}

export interface FirstPlacePrediction {
  title: string;
  org: string;
  area: string | null;
  assessment_rate: number;
  first_place_rate: number;
  first_place_amount: number;
  date: string;
}

export interface AnalysisCompanyRatesResponse {
  company_rates: CompanyRateRecord[];
  gaps: GapItem[];
  largest_gap_midpoint: number | null;
  refined_rate: number | null;
  total_companies: number;
  unique_rate_count: number;
  first_place_predictions: FirstPlacePrediction[];
  next_year_validation: unknown[];
}

export interface ComprehensiveComparison {
  id: string;
  title: string;
  org: string;
  area: string | null;
  date: string;
  assessment_rate: number;
  first_place_rate: number | null;
  predicted_rate: number;
  predicted_diff: number;
  actual_first_diff: number;
  is_match: boolean;
  rank?: number | null;   // 낙찰순위 (KBID 동등성 §1)
  first_place_amount: number | null;
}

export interface ComprehensivePeriodResult {
  period_months: number;
  match_count: number;
  total: number;
  match_rate: number;
  comparisons: ComprehensiveComparison[];
}

export interface AnalysisComprehensiveResponse {
  announcement: AnnouncementMeta;
  confirmed_rate: number | null;
  predicted_first_place: { rate: number; amount: number } | null;
  period_results: Record<string, ComprehensivePeriodResult>;
}

export interface TrendPoint {
  period: string;
  avg_rate: number;
  min_rate: number;
  max_rate: number;
  count: number;
}

export interface AnalysisTrendResponse {
  announcement: AnnouncementMeta;
  params: {
    granularity: string;
    period_months: number;
    category_filter: string;
  };
  series: TrendPoint[];
}

export interface PreliminaryFreqBin {
  number: number;
  count: number;
  percentage: number;
}

export interface AnalysisPreliminaryFrequencyResponse {
  bins: PreliminaryFreqBin[];
  total_cases: number;
  peak_numbers: number[];
  selected_per_case: number;
}

export interface CorrelationMethod {
  name: string;
  top1_rate: number;
  top1_score: number;
  count: number;
  weighted_count: number;
  outliers_removed: number;
  homogeneity: number;
  mode: string;
}

export interface CorrelationSummary {
  agreement: number;
  final_top1: number;
  predicted_bid_amount: number;
  methods_aligned: string[];
  confidence: {
    score: number;
    level: string;
    reasons: string[];
  };
  sample_size: number;
  raw_sample_size: number;
  outliers_removed: number;
  homogeneity: number;
  std_deviation: number;
  confidence_interval: {
    mean: number;
    lower: number;
    upper: number;
    margin: number;
  };
}

export interface AnalysisCorrelationResponse {
  announcement: AnnouncementMeta;
  params: Record<string, unknown>;
  methods: CorrelationMethod[];
  correlation: CorrelationSummary;
}

export interface AnalysisSearchFilters {
  org_search: string;
  price_volatility_min: number;
  price_volatility_max: number;
  base_amount: number | null;
  category_filter: string;
  period_months: number;
}
