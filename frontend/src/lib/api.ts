const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

function getAuthHeader(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = window.localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeader(),
      ...(options?.headers as Record<string, string> | undefined),
    },
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: "요청 실패" }));
    throw new Error(error.detail || `HTTP ${res.status}`);
  }

  return res.json();
}

export const api = {
  // 공고
  getAnnouncements: (params: Record<string, string | number>) => {
    const query = new URLSearchParams(
      Object.entries(params)
        .filter(([, v]) => v !== "" && v !== undefined)
        .map(([k, v]) => [k, String(v)])
    ).toString();
    return fetchApi<AnnouncementListResponse>(`/api/v1/announcements?${query}`);
  },

  getAnnouncement: (id: string) =>
    fetchApi<AnnouncementResponse>(`/api/v1/announcements/${id}`),

  // 예측
  createPrediction: (announcementId: string) =>
    fetchApi<PredictionDetailResponse>("/api/v1/predictions", {
      method: "POST",
      body: JSON.stringify({ announcement_id: announcementId }),
    }),

  getPrediction: (id: string) =>
    fetchApi<PredictionResponse>(`/api/v1/predictions/${id}`),

  // 통계
  getKPI: () => fetchApi<DashboardKPI>("/api/v1/stats/kpi"),
  getTrends: (months?: number) =>
    fetchApi<TrendResponse>(`/api/v1/stats/trends?months=${months || 6}`),
  getRegionStats: () => fetchApi<RegionStatsResponse>("/api/v1/stats/by-region"),
  getIndustryStats: () =>
    fetchApi<IndustryStatsResponse>("/api/v1/stats/by-industry"),

  // 관리자
  getAdminDashboard: () => fetchApi<AdminDashboard>("/api/v1/admin/dashboard"),
  triggerRetrain: () =>
    fetchApi<{ message: string }>("/api/v1/admin/retrain", { method: "POST" }),
  triggerSync: (source: string) =>
    fetchApi<{ message: string }>(`/api/v1/admin/sync?source=${source}`, {
      method: "POST",
    }),

  // 분석
  analysis: {
    getFrequency: (id: string, params?: Record<string, string | number>) => {
      const query = params
        ? "?" +
          new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v !== "" && v !== undefined)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return fetchApi<import("@/types/analysis").AnalysisFrequencyResponse>(
        `/api/v1/analysis/frequency/${id}${query}`
      );
    },

    getRateBuckets: (id: string, params?: Record<string, string | number>) => {
      const query = params
        ? "?" +
          new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v !== "" && v !== undefined)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return fetchApi<import("@/types/analysis").AnalysisRateBucketsResponse>(
        `/api/v1/analysis/rate-buckets/${id}${query}`
      );
    },

    getCompanyRates: (id: string, params?: Record<string, string | number>) => {
      const query = params
        ? "?" +
          new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v !== "" && v !== undefined)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return fetchApi<import("@/types/analysis").AnalysisCompanyRatesResponse>(
        `/api/v1/analysis/company-rates/${id}${query}`
      );
    },

    getComprehensive: (id: string, params?: Record<string, string | number>) => {
      const query = params
        ? "?" +
          new URLSearchParams(
            Object.entries(params)
              .filter(([, v]) => v !== "" && v !== undefined)
              .map(([k, v]) => [k, String(v)])
          ).toString()
        : "";
      return fetchApi<import("@/types/analysis").AnalysisComprehensiveResponse>(
        `/api/v1/analysis/comprehensive/${id}${query}`
      );
    },

    getTrend: (id: string) =>
      fetchApi<import("@/types/analysis").AnalysisTrendResponse>(
        `/api/v1/analysis/trend/${id}`
      ),

    getPreliminaryFrequency: (id: string) =>
      fetchApi<import("@/types/analysis").AnalysisPreliminaryFrequencyResponse>(
        `/api/v1/analysis/preliminary-frequency/${id}`
      ),

    getCorrelation: (id: string) =>
      fetchApi<import("@/types/analysis").AnalysisCorrelationResponse>(
        `/api/v1/analysis/correlation/${id}`
      ),

    exportExcel: async (
      type: "buckets" | "company" | "correlation" | "bid_list",
      id: string,
      extraParams?: Record<string, string | number>
    ) => {
      const qs = new URLSearchParams({ announcement_id: id });
      if (extraParams) {
        for (const [k, v] of Object.entries(extraParams)) {
          qs.set(k, String(v));
        }
      }
      const res = await fetch(
        `${API_BASE}/api/v1/analysis/export/${type}?${qs.toString()}`,
        { headers: getAuthHeader() }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "엑셀 다운로드 실패" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cd = res.headers.get("content-disposition") ?? "";
      const m = cd.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
      a.download = m ? decodeURIComponent(m[1]) : `${type}_${id}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    },
  },
};

// Types
export interface AnnouncementResponse {
  id: string;
  source: string;
  bid_number: string;
  category: string;
  title: string;
  ordering_org_name: string;
  ordering_org_type: string | null;
  region: string | null;
  base_amount: number | null;
  estimated_price: number | null;
  bid_method: string | null;
  announced_at: string | null;
  deadline_at: string | null;
  status: string | null;
  assessment_rate: number | null;
  winning_amount: number | null;
}

export interface AnnouncementListResponse {
  items: AnnouncementResponse[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface PredictionResponse {
  id: string;
  announcement_id: string;
  announcement_title: string | null;
  category: string | null;
  region: string | null;
  base_amount: number | null;
  predicted_assessment_rate: number;
  confidence_lower: number | null;
  confidence_upper: number | null;
  predicted_winning_amount: number | null;
  model_version: string | null;
  model_type: string | null;
  confidence_score: number | null;
  features_used: Record<string, string> | null;
  feature_importance: { feature: string; importance: number }[] | null;
  created_at: string;
}

export interface SimilarBidResponse {
  bid_number: string;
  title: string;
  category: string;
  region: string | null;
  base_amount: number | null;
  assessment_rate: number | null;
  winning_amount: number | null;
  opened_at: string | null;
}

export interface PredictionDetailResponse {
  prediction: PredictionResponse;
  similar_bids: SimilarBidResponse[];
}

export interface DashboardKPI {
  total_announcements: number;
  today_announcements: number;
  construction_count: number;
  service_count: number;
  defense_count: number;
  avg_assessment_rate: number | null;
}

export interface TrendDataPoint {
  period: string;
  construction_rate: number | null;
  service_rate: number | null;
  total_rate: number | null;
  count: number;
}

export interface TrendResponse {
  data: TrendDataPoint[];
  period_type: string;
}

export interface RegionStat {
  region: string;
  avg_rate: number;
  count: number;
  min_rate: number | null;
  max_rate: number | null;
}

export interface RegionStatsResponse {
  data: RegionStat[];
}

export interface IndustryStatsResponse {
  data: { industry_code: string; industry_name: string; avg_rate: number; count: number }[];
}

export interface PipelineStatus {
  name: string;
  source: string;
  sync_type: string;
  status: string;
  last_run: string | null;
  records_count: string | null;
  next_run: string | null;
}

export interface ModelPerformance {
  model_version: string;
  model_type: string;
  trained_at: string;
  training_samples: number;
  mae: number | null;
  rmse: number | null;
  r_squared: number | null;
  is_active: boolean;
}

export interface AdminDashboard {
  total_users: number;
  premium_users: number;
  today_api_calls: number;
  total_announcements: number;
  total_results: number;
  pipelines: PipelineStatus[];
  model_history: ModelPerformance[];
}
