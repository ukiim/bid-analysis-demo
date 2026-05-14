"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type {
  AnnouncementMeta,
  AnalysisSearchFilters,
  FrequencyStats,
  FrequencyBin,
  PredictionCandidate,
  AnalysisRateBucketsResponse,
  ComprehensiveComparison,
  AnalysisComprehensiveResponse,
  TrendPoint,
  PreliminaryFreqBin,
  FirstPlacePrediction,
  AnalysisCompanyRatesResponse,
  AnalysisCorrelationResponse,
} from "@/types/analysis";

import AnalysisHeader from "@/components/analysis/AnalysisHeader";
import AnalysisFilterPanel from "@/components/analysis/AnalysisFilterPanel";
import AnalysisSummaryBar from "@/components/analysis/AnalysisSummaryBar";
import AnalysisDataTable from "@/components/analysis/AnalysisDataTable";
import AnalysisTabs from "@/components/analysis/AnalysisTabs";
import AnalysisCalculator from "@/components/analysis/AnalysisCalculator";
import Tab1RateChart from "@/components/analysis/tabs/Tab1RateChart";
import Tab2PreliminaryFreq from "@/components/analysis/tabs/Tab2PreliminaryFreq";
import Tab3FrequencyMatrix from "@/components/analysis/tabs/Tab3FrequencyMatrix";
import Tab5CompanyRates from "@/components/analysis/tabs/Tab5CompanyRates";
import Tab6Comprehensive from "@/components/analysis/tabs/Tab6Comprehensive";
import BidListPanel from "@/components/bid-list/BidListPanel";
import { addToBidList, loadBidList } from "@/lib/bidList";

const DEFAULT_FILTERS: AnalysisSearchFilters = {
  org_search: "",
  price_volatility_min: -3,
  price_volatility_max: 3,
  base_amount: null,
  category_filter: "all",
  period_months: 12,
};

export default function AnalysisPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [filters, setFilters] = useState<AnalysisSearchFilters>(() => {
    const period = searchParams.get("period_months");
    const cat = searchParams.get("category");
    const org = searchParams.get("org");
    return {
      ...DEFAULT_FILTERS,
      period_months: period ? Number(period) : DEFAULT_FILTERS.period_months,
      category_filter: cat ?? DEFAULT_FILTERS.category_filter,
      org_search: org ?? DEFAULT_FILTERS.org_search,
    };
  });
  const [activeTab, setActiveTab] = useState(searchParams.get("tab") ?? "tab3");
  const [selectedRate, setSelectedRate] = useState<number | null>(() => {
    const r = searchParams.get("rate");
    return r ? Number(r) : null;
  });

  // Sync state -> URL (replace, not push, to avoid history clutter)
  useEffect(() => {
    const params = new URLSearchParams();
    if (filters.period_months !== DEFAULT_FILTERS.period_months)
      params.set("period_months", String(filters.period_months));
    if (filters.category_filter !== DEFAULT_FILTERS.category_filter)
      params.set("category", filters.category_filter);
    if (filters.org_search) params.set("org", filters.org_search);
    if (activeTab !== "tab3") params.set("tab", activeTab);
    if (selectedRate != null) params.set("rate", selectedRate.toFixed(4));
    const qs = params.toString();
    const url = qs ? `?${qs}` : window.location.pathname;
    router.replace(url, { scroll: false });
  }, [filters.period_months, filters.category_filter, filters.org_search, activeTab, selectedRate, router]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data state
  const [announcement, setAnnouncement] = useState<AnnouncementMeta | null>(null);
  const [freqBins, setFreqBins] = useState<FrequencyBin[]>([]);
  const [freqStats, setFreqStats] = useState<FrequencyStats | null>(null);
  const [predictionCandidates, setPredictionCandidates] = useState<PredictionCandidate[]>([]);
  const [dataCount, setDataCount] = useState(0);
  const [rateBuckets, setRateBuckets] = useState<AnalysisRateBucketsResponse | null>(null);
  const [comparisons, setComparisons] = useState<ComprehensiveComparison[]>([]);
  const [trendSeries, setTrendSeries] = useState<TrendPoint[]>([]);
  const [prelimBins, setPrelimBins] = useState<PreliminaryFreqBin[]>([]);
  const [prelimTotal, setPrelimTotal] = useState(0);
  const [firstPlacePreds, setFirstPlacePreds] = useState<FirstPlacePrediction[]>([]);
  const [companyData, setCompanyData] = useState<AnalysisCompanyRatesResponse | null>(null);
  const [correlation, setCorrelation] = useState<AnalysisCorrelationResponse | null>(null);
  const [comprehensiveData, setComprehensiveData] = useState<AnalysisComprehensiveResponse | null>(null);
  const [bidListOpen, setBidListOpen] = useState(false);
  const [bidListCount, setBidListCount] = useState(0);
  useEffect(() => {
    if (typeof window !== "undefined") setBidListCount(loadBidList().length);
  }, [bidListOpen]);

  const fetchAll = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    setError(null);

    const params: Record<string, string | number> = {
      period_months: filters.period_months,
      category_filter: filters.category_filter,
    };
    if (filters.org_search) params.org_search = filters.org_search;

    // KBID 동등성 (1차 데모 검토 §1): frequency 호출에 bin_size + 동일공종/동일발주처 풀 설정
    const freqParams: Record<string, string | number> = {
      ...params,
      bin_size: 0.01,
      org_scope: filters.org_search === "all" ? "all" : "specific",
    };

    try {
      const [freq, buckets, comprehensive, trend, prelim, company, corr] =
        await Promise.allSettled([
          api.analysis.getFrequency(id, freqParams),
          api.analysis.getRateBuckets(id, params),
          api.analysis.getComprehensive(id, params),
          api.analysis.getTrend(id),
          api.analysis.getPreliminaryFrequency(id),
          api.analysis.getCompanyRates(id, params),
          api.analysis.getCorrelation(id),
        ]);

      if (freq.status === "fulfilled") {
        setAnnouncement(freq.value.announcement);
        setFreqBins(freq.value.bins);
        setFreqStats(freq.value.stats);
        setPredictionCandidates(freq.value.prediction_candidates);
        setDataCount(freq.value.data_count);
      }

      if (buckets.status === "fulfilled") {
        setRateBuckets(buckets.value);
      }

      if (comprehensive.status === "fulfilled") {
        setComprehensiveData(comprehensive.value);
        const allComparisons: ComprehensiveComparison[] = [];
        for (const period of Object.values(comprehensive.value.period_results)) {
          allComparisons.push(...period.comparisons);
        }
        setComparisons(allComparisons);
        if (!announcement) setAnnouncement(comprehensive.value.announcement);
      }

      if (trend.status === "fulfilled") {
        setTrendSeries(trend.value.series);
        if (!announcement) setAnnouncement(trend.value.announcement);
      }

      if (prelim.status === "fulfilled") {
        setPrelimBins(prelim.value.bins);
        setPrelimTotal(prelim.value.total_cases);
      }

      if (company.status === "fulfilled") {
        setCompanyData(company.value);
        setFirstPlacePreds(company.value.first_place_predictions ?? []);
      }

      if (corr.status === "fulfilled") {
        setCorrelation(corr.value);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "데이터 로딩 실패");
    } finally {
      setLoading(false);
    }
  }, [id, filters.period_months, filters.category_filter, filters.org_search]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const handleAddToBidList = () => {
    if (!announcement || selectedRate == null) {
      alert("먼저 사정률을 선택해주세요 (Tab3 매트릭스 셀 또는 차트 클릭)");
      return;
    }
    const bidAmount = announcement.budget
      ? Math.round(announcement.budget * (selectedRate / 100))
      : null;
    const next = addToBidList({
      announcement_id: announcement.id,
      title: announcement.title,
      org: announcement.org ?? "-",
      base_amount: announcement.budget ?? null,
      predicted_rate: selectedRate,
      predicted_bid_amount: bidAmount,
      adjustment: 0,
      added_at: new Date().toISOString(),
    });
    setBidListCount(next.length);
    alert(`투찰리스트에 추가됨 (총 ${next.length}건)`);
  };

  const handleExport = async () => {
    if (!id) return;
    try {
      await api.analysis.exportExcel("correlation", id, {
        period_months: filters.period_months,
        category_filter: filters.category_filter,
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "엑셀 다운로드 실패");
    }
  };

  // v5 — PDF 정합화: 5탭 (업체사정률을 메인 탭으로 승격, 보조 모드 제거)
  const tabs = [
    {
      key: "tab1",
      label: "사정률 그래프 분석",
      content: <Tab1RateChart series={trendSeries} selectedRate={selectedRate} />,
    },
    {
      key: "tab2",
      label: "추첨된 예가빈도수 분석",
      content: <Tab2PreliminaryFreq bins={prelimBins} total={prelimTotal} />,
    },
    {
      key: "tab3",
      label: "사정률 발생빈도와 구간분석",
      content: (
        <Tab3FrequencyMatrix
          bins={freqBins}
          stats={freqStats ?? { mean: 0, median: 0, std: 0, min: 0, max: 0 }}
          predictionCandidates={predictionCandidates}
          rateBuckets={rateBuckets}
          companyData={companyData}
          selectedRate={selectedRate}
          onRateSelect={setSelectedRate}
        />
      ),
    },
    {
      key: "tab4",
      label: "업체사정률 분석",
      content: (
        <Tab5CompanyRates
          data={companyData}
          selectedRate={selectedRate}
          onRateSelect={setSelectedRate}
        />
      ),
    },
    {
      key: "tab5",
      label: "종합분석",
      content: (
        <Tab6Comprehensive
          announcement={announcement}
          rateBuckets={rateBuckets}
          correlation={correlation}
          comprehensive={comprehensiveData}
          selectedRate={selectedRate}
          onRateSelect={setSelectedRate}
        />
      ),
    },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="w-8 h-8 border-4 border-[#3358A4] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <div className="text-[13px] text-gray-500">분석 데이터 로딩 중...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="text-red-500 text-lg mb-2">⚠</div>
          <div className="text-[13px] text-red-600">{error}</div>
          <button
            onClick={fetchAll}
            className="mt-3 px-4 py-1.5 bg-[#3358A4] text-white text-[12px] hover:bg-[#2C4F8A]"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* v5: 투찰리스트 액션 (PDF 03 §9) */}
      <div className="mx-4 flex items-center justify-end gap-2 mb-2">
        <button
          onClick={handleAddToBidList}
          className="kbid-btn-secondary"
          style={{ padding: "5px 12px", fontSize: 12 }}
          title="현재 선택 사정률을 투찰리스트에 추가"
        >
          ➕ 투찰리스트 담기
        </button>
        <button
          onClick={() => setBidListOpen(true)}
          className="kbid-btn-primary"
          style={{ padding: "5px 14px", fontSize: 12 }}
        >
          📋 투찰리스트 보기 ({bidListCount})
        </button>
      </div>

      {bidListOpen && <BidListPanel onClose={() => setBidListOpen(false)} />}

      <AnalysisHeader announcement={announcement} />

      <AnalysisFilterPanel
        announcement={announcement}
        filters={filters}
        dataCount={dataCount}
        onFiltersChange={setFilters}
        onSearch={fetchAll}
      />

      <AnalysisSummaryBar
        stats={freqStats}
        dataCount={dataCount}
        onExport={handleExport}
      />

      <AnalysisDataTable comparisons={comparisons} />

      {/* v5: PDF 정합 5-탭 (보조 모드 제거) */}
      <AnalysisTabs
        tabs={tabs}
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />

      <AnalysisCalculator
        baseAmount={announcement?.budget ?? null}
        selectedRate={selectedRate}
      />
    </div>
  );
}
