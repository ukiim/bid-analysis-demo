"use client";

import { useMemo } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import type {
  FrequencyBin,
  FrequencyStats,
  PredictionCandidate,
  AnalysisRateBucketsResponse,
  AnalysisCompanyRatesResponse,
} from "@/types/analysis";

interface Props {
  bins: FrequencyBin[];
  stats: FrequencyStats;
  predictionCandidates: PredictionCandidate[];
  rateBuckets: AnalysisRateBucketsResponse | null;
  companyData: AnalysisCompanyRatesResponse | null;
  selectedRate: number | null;
  onRateSelect: (rate: number) => void;
}

export default function Tab3FrequencyMatrix({
  bins,
  stats,
  predictionCandidates,
  rateBuckets,
  companyData,
  selectedRate,
  onRateSelect,
}: Props) {
  const chartData = useMemo(
    () =>
      bins.map((b) => ({
        rate: b.rate.toFixed(1),
        count: b.count,
        first_place: b.first_place_count,
      })),
    [bins]
  );

  // KBID 동등성 (1차 데모 검토 §1): 0.01% 정밀도 매트릭스
  // 행: 정수부 사정률 (예: 99, 100, 101) · 열: 소수 .00 ~ .99 (100컬럼)
  // bins[].rate 가 이미 0.01 단위 (백엔드 bin_size=0.01) — 정렬해서 매핑
  const matrixRows = useMemo(() => {
    const rows: { label: string; cells: { rate: number; count: number }[] }[] = [];
    if (bins.length === 0) return rows;
    const sorted = [...bins].sort((a, b) => a.rate - b.rate);
    const minRate = Math.floor(sorted[0].rate);
    const maxRate = Math.ceil(sorted[sorted.length - 1].rate);

    // bins 를 round(rate*100) 키로 인덱싱 (0.01 정밀도 매칭)
    const binMap = new Map<number, number>();
    for (const b of bins) {
      const key = Math.round(b.rate * 100);
      binMap.set(key, (binMap.get(key) ?? 0) + b.count);
    }

    for (let intPart = minRate; intPart <= maxRate; intPart++) {
      const cells: { rate: number; count: number }[] = [];
      for (let dec = 0; dec < 100; dec++) {
        const r = intPart + dec * 0.01;
        const key = Math.round(r * 100);
        cells.push({ rate: r, count: binMap.get(key) ?? 0 });
      }
      rows.push({ label: `${intPart}`, cells });
    }
    return rows;
  }, [bins]);

  return (
    <div>
      <div className="text-[13px] font-bold text-[#437194] mb-3">
        사정률 발생빈도와 구간분석
      </div>

      {/* Histogram */}
      <ResponsiveContainer width="100%" height={250}>
        <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
          <XAxis dataKey="rate" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
          <YAxis tick={{ fontSize: 10 }} />
          <Tooltip contentStyle={{ fontSize: 11 }} />
          <Bar dataKey="count" fill="#437194" name="빈도" radius={[1, 1, 0, 0]} />
          <Bar dataKey="first_place" fill="#E8913A" name="1순위" radius={[1, 1, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>

      {/* Interactive matrix (KBID 동등성: 0.01% 정밀도 — 100컬럼 × N행) */}
      <div className="mt-4 overflow-x-auto border border-gray-300">
        <table className="border-collapse text-[10px]">
          <thead>
            <tr>
              <th className="border border-gray-300 bg-[#E8EDF3] px-1.5 py-1 text-center font-semibold sticky left-0 z-10 min-w-[44px]">
                %
              </th>
              {Array.from({ length: 100 }, (_, i) => (
                <th
                  key={i}
                  className="border border-gray-300 bg-[#E8EDF3] px-0 py-1 text-center font-semibold min-w-[26px]"
                >
                  .{i.toString().padStart(2, "0")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrixRows.map((row) => (
              <tr key={row.label}>
                <td className="border border-gray-300 bg-[#E8EDF3] px-1.5 py-1 text-center font-bold sticky left-0 z-10">
                  {row.label}
                </td>
                {row.cells.map((cell) => {
                  const isSelected =
                    selectedRate != null &&
                    Math.abs(cell.rate - selectedRate) < 0.005;
                  return (
                    <td
                      key={cell.rate}
                      onClick={() => cell.count > 0 && onRateSelect(cell.rate)}
                      title={`${cell.rate.toFixed(2)}% · ${cell.count}건`}
                      className={`border border-gray-300 px-0 py-0.5 text-center transition-colors ${
                        isSelected
                          ? "bg-[#437194] text-white font-bold cursor-pointer"
                          : cell.count > 0
                          ? "bg-[#E8913A] text-white font-semibold cursor-pointer"
                          : "text-gray-200"
                      }`}
                    >
                      {cell.count > 0 ? cell.count : ""}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* 매트릭스 가이드 — KBID 캡쳐 동등성 */}
      <div className="mt-1.5 text-[10px] text-gray-500 flex items-center gap-3">
        <span>← 가로 스크롤로 .00 ~ .99 (0.01% 단위 100컬럼) 전체 확인</span>
        {selectedRate != null && (
          <span className="text-[#437194] font-bold">
            선택: {selectedRate.toFixed(2)}%
          </span>
        )}
      </div>

      {/* Rate buckets (A/B/C modes) */}
      {rateBuckets && (
        <div className="mt-4 grid grid-cols-3 gap-3">
          {(["A", "B", "C"] as const).map((mode) => {
            const items = rateBuckets.buckets[mode];
            const modeLabel =
              mode === "A" ? "빈도최대" : mode === "B" ? "공백" : "차이최대";
            return (
              <div key={mode} className="border border-gray-300">
                <div className="bg-gradient-to-b from-[#5481B8] to-[#437194] text-white px-3 py-1.5 text-[11px] font-bold">
                  구간 {mode} — {modeLabel}
                </div>
                <table className="w-full border-collapse text-[11px]">
                  <thead>
                    <tr className="bg-[#E8EDF3]">
                      <th className="border border-gray-300 px-2 py-1">순위</th>
                      <th className="border border-gray-300 px-2 py-1">사정률</th>
                      <th className="border border-gray-300 px-2 py-1">방향</th>
                      <th className="border border-gray-300 px-2 py-1">점수</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.slice(0, 5).map((item, i) => (
                      <tr
                        key={i}
                        onClick={() => onRateSelect(item.rate)}
                        className="cursor-pointer hover:bg-blue-50"
                      >
                        <td className="border border-gray-300 px-2 py-1 text-center font-bold text-[#437194]">
                          {item.rank}
                        </td>
                        <td className="border border-gray-300 px-2 py-1 text-center font-semibold">
                          {item.rate.toFixed(2)}%
                        </td>
                        <td className="border border-gray-300 px-2 py-1 text-center">
                          {item.side === "+" ? "↑" : item.side === "-" ? "↓" : "="}
                        </td>
                        <td className="border border-gray-300 px-2 py-1 text-center">
                          {item.score}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}

      {/* Prediction candidates */}
      {predictionCandidates.length > 0 && (
        <div className="mt-4">
          <div className="text-[12px] font-bold text-gray-700 mb-2">
            예측값 선택
          </div>
          <div className="flex flex-wrap gap-2">
            {predictionCandidates.slice(0, 10).map((c) => (
              <button
                key={c.rank}
                onClick={() => onRateSelect(c.rate)}
                className={`px-3 py-1.5 text-[11px] border transition-colors ${
                  c.is_recommended
                    ? "bg-[#E8913A] text-white border-[#E8913A] font-bold"
                    : selectedRate != null && Math.abs(c.rate - selectedRate) < 0.05
                    ? "bg-[#437194] text-white border-[#437194]"
                    : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                }`}
              >
                {c.rank}위: {c.rate.toFixed(4)}%
                {c.is_recommended && " ★"}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Company gap analysis */}
      {companyData && (companyData.gaps?.length > 0 || companyData.refined_rate != null) && (
        <div className="mt-4 border border-gray-300">
          <div className="bg-gradient-to-b from-[#5481B8] to-[#437194] text-white px-3 py-1.5 text-[11px] font-bold flex items-center justify-between">
            <span>업체사정률 갭 분석</span>
            <span className="text-[10px] opacity-90">
              업체 {companyData.total_companies}곳 · 고유사정률 {companyData.unique_rate_count}건
            </span>
          </div>
          <div className="p-3">
            {companyData.refined_rate != null && (
              <div className="mb-3 flex items-center gap-3 text-[11px]">
                <span className="bg-[#E8EDF3] px-2 py-1 font-semibold text-gray-700">세밀 사정률</span>
                <button
                  onClick={() => onRateSelect(companyData.refined_rate!)}
                  className="px-3 py-1 bg-[#E8913A] text-white font-bold hover:bg-[#D17F2A]"
                >
                  {companyData.refined_rate.toFixed(4)}%
                </button>
                {companyData.largest_gap_midpoint != null && (
                  <>
                    <span className="bg-[#E8EDF3] px-2 py-1 font-semibold text-gray-700 ml-2">최대 갭 중간값</span>
                    <button
                      onClick={() => onRateSelect(companyData.largest_gap_midpoint!)}
                      className="px-3 py-1 bg-white border border-[#437194] text-[#437194] font-bold hover:bg-blue-50"
                    >
                      {companyData.largest_gap_midpoint.toFixed(4)}%
                    </button>
                  </>
                )}
              </div>
            )}
            {companyData.gaps && companyData.gaps.length > 0 && (
              <table className="w-full border-collapse text-[11px]">
                <thead>
                  <tr className="bg-[#E8EDF3]">
                    <th className="border border-gray-300 px-2 py-1 text-center">No</th>
                    <th className="border border-gray-300 px-2 py-1 text-center">시작</th>
                    <th className="border border-gray-300 px-2 py-1 text-center">끝</th>
                    <th className="border border-gray-300 px-2 py-1 text-center">갭 크기</th>
                    <th className="border border-gray-300 px-2 py-1 text-center">중간값</th>
                  </tr>
                </thead>
                <tbody>
                  {companyData.gaps.slice(0, 8).map((g, i) => (
                    <tr
                      key={i}
                      onClick={() => onRateSelect(g.midpoint)}
                      className="cursor-pointer hover:bg-blue-50"
                    >
                      <td className="border border-gray-300 px-2 py-1 text-center text-gray-500">{i + 1}</td>
                      <td className="border border-gray-300 px-2 py-1 text-center">{g.start.toFixed(4)}%</td>
                      <td className="border border-gray-300 px-2 py-1 text-center">{g.end.toFixed(4)}%</td>
                      <td className="border border-gray-300 px-2 py-1 text-center font-semibold text-[#E8913A]">
                        {g.size.toFixed(4)}
                      </td>
                      <td className="border border-gray-300 px-2 py-1 text-center font-bold text-[#437194]">
                        {g.midpoint.toFixed(4)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      )}

      {/* Stats summary */}
      <div className="mt-4 flex items-center gap-6 text-[11px] text-gray-600 border-t border-gray-200 pt-3">
        <span>평균: <b>{stats.mean.toFixed(4)}%</b></span>
        <span>중간값: <b>{stats.median.toFixed(4)}%</b></span>
        <span>표준편차: <b>{stats.std.toFixed(4)}</b></span>
        <span>최소: <b>{stats.min.toFixed(4)}%</b></span>
        <span>최대: <b>{stats.max.toFixed(4)}%</b></span>
        {rateBuckets?.detail_rate != null && (
          <span className="text-[#437194] font-bold">
            세부값: {rateBuckets.detail_rate.toFixed(4)}%
          </span>
        )}
      </div>
    </div>
  );
}
