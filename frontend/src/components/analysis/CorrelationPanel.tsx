"use client";

import type { AnalysisCorrelationResponse } from "@/types/analysis";

interface Props {
  data: AnalysisCorrelationResponse | null;
  onRateSelect: (rate: number) => void;
}

const METHOD_COLORS = ["#3358A4", "#4A7ABF", "#7C9CD1"];

export default function CorrelationPanel({ data, onRateSelect }: Props) {
  if (!data) return null;

  const { methods, correlation } = data;
  const conf = correlation.confidence;
  const confColor =
    conf.level === "high"
      ? "#4CAF50"
      : conf.level === "medium"
      ? "#E8913A"
      : "#9E9E9E";

  return (
    <div className="mx-4 mt-2 bg-white border border-gray-300">
      <div className="bg-gradient-to-b from-[#4A7ABF] to-[#3358A4] text-white px-4 py-2 text-[12px] font-bold flex items-center justify-between">
        <span>상관관계 분석 — 3가지 방법 종합</span>
        <span className="text-[10px] opacity-90">
          표본 {correlation.sample_size.toLocaleString()}건 · 이상치 {correlation.outliers_removed}건 제거
        </span>
      </div>
      <div className="p-3">
        {/* 3 method cards */}
        <div className="grid grid-cols-3 gap-2 mb-3">
          {methods.map((m, i) => {
            const aligned = correlation.methods_aligned.includes(m.name);
            return (
              <div
                key={i}
                onClick={() => onRateSelect(m.top1_rate)}
                className={`border-2 cursor-pointer transition-colors ${
                  aligned ? "border-[#E8913A] bg-[#FFF7ED]" : "border-gray-200 bg-white hover:bg-gray-50"
                }`}
              >
                <div
                  className="px-2 py-1 text-white text-[10px] font-bold"
                  style={{ backgroundColor: METHOD_COLORS[i] ?? "#3358A4" }}
                >
                  {m.name}
                </div>
                <div className="p-2">
                  <div className="text-[10px] text-gray-500">예측 1순위</div>
                  <div className="text-[18px] font-extrabold text-[#3358A4]">
                    {m.top1_rate.toFixed(4)}%
                  </div>
                  <div className="text-[10px] text-gray-500 mt-1.5 flex justify-between">
                    <span>점수 {m.top1_score.toLocaleString()}</span>
                    <span>표본 {m.count.toLocaleString()}건</span>
                  </div>
                  {m.mode && (
                    <div className="text-[10px] text-gray-400 mt-0.5">모드 {m.mode}</div>
                  )}
                  {aligned && (
                    <div className="text-[10px] text-[#E8913A] font-bold mt-1">★ 종합 일치</div>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        {/* Summary row */}
        <div className="flex items-center gap-4 bg-[#E8EDF3] border border-gray-300 px-3 py-2">
          <div className="flex items-baseline gap-2">
            <span className="text-[11px] font-semibold text-gray-700">종합 1순위</span>
            <button
              onClick={() => onRateSelect(correlation.final_top1)}
              className="px-3 py-1 bg-[#E8913A] text-white text-[14px] font-extrabold hover:bg-[#D17F2A]"
            >
              {correlation.final_top1.toFixed(4)}%
            </button>
          </div>
          <div className="flex items-baseline gap-1.5">
            <span className="text-[11px] font-semibold text-gray-700">예상 투찰</span>
            <span className="text-[13px] font-bold text-[#3358A4]">
              {correlation.predicted_bid_amount.toLocaleString()}원
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-semibold text-gray-700">합치도</span>
            <span className="text-[12px] font-bold">
              {(correlation.agreement * 100).toFixed(0)}%
            </span>
            <span className="text-[10px] text-gray-500">
              ({correlation.methods_aligned.length}/3 일치)
            </span>
          </div>
          <div className="flex items-center gap-1.5 ml-auto">
            <span
              className="px-2 py-1 text-white text-[10px] font-bold"
              style={{ backgroundColor: confColor }}
            >
              신뢰도 {conf.level === "high" ? "높음" : conf.level === "medium" ? "중간" : "낮음"} {conf.score}
            </span>
          </div>
        </div>

        {/* Confidence interval & reasons */}
        <div className="mt-2 grid grid-cols-2 gap-2 text-[10px]">
          <div className="border border-gray-200 px-2 py-1.5">
            <div className="text-gray-500 mb-0.5">95% 신뢰구간</div>
            <div className="font-bold text-gray-700">
              {correlation.confidence_interval.lower.toFixed(4)}% ~ {correlation.confidence_interval.upper.toFixed(4)}%
              <span className="ml-1 text-gray-400">
                (±{correlation.confidence_interval.margin.toFixed(4)})
              </span>
            </div>
          </div>
          <div className="border border-gray-200 px-2 py-1.5">
            <div className="text-gray-500 mb-0.5">판단 근거</div>
            <div className="text-gray-700">{conf.reasons.join(" · ")}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
