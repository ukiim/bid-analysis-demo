"use client";

/**
 * 사정률 예측 페이지 — v4 KBID 톤 (form-table 기반)
 */
import { useState } from "react";
import AmLineChart from "@/components/charts/AmLineChart";

const PREDICTION_TARGETS = [
  {
    id: "A2024-8821", title: "한강변 보행로 정비공사",
    budget: 38500, type: "공사", area: "서울",
    predRate: 84.2, predMin: 82.1, predMax: 86.4,
    bidAmountPred: 32427, bidMin: 31628, bidMax: 33264,
    confidence: 87,
  },
  {
    id: "A2024-8819", title: "부산항 항만시설 확장공사",
    budget: 152000, type: "공사", area: "부산",
    predRate: 79.3, predMin: 77.0, predMax: 81.7,
    bidAmountPred: 120536, bidMin: 117040, bidMax: 124184,
    confidence: 82,
  },
  {
    id: "A2024-8820", title: "국방과학연구소 시설유지보수 용역",
    budget: 12200, type: "용역", area: "대전",
    predRate: 91.5, predMin: 89.8, predMax: 93.2,
    bidAmountPred: 11163, bidMin: 10956, bidMax: 11370,
    confidence: 91,
  },
];

const TREND_DATA = [
  { period: "10월", avg_rate: 85.3, min_rate: 82.4, max_rate: 88.1 },
  { period: "11월", avg_rate: 84.1, min_rate: 80.9, max_rate: 87.3 },
  { period: "12월", avg_rate: 84.4, min_rate: 79.5, max_rate: 89.2 },
  { period: "1월", avg_rate: 86.8, min_rate: 83.1, max_rate: 90.4 },
  { period: "2월", avg_rate: 85.3, min_rate: 81.7, max_rate: 88.8 },
  { period: "3월", avg_rate: 87.8, min_rate: 84.3, max_rate: 91.2 },
];

export default function PredictionPage() {
  const [selected, setSelected] = useState(PREDICTION_TARGETS[0]);

  return (
    <div>
      {/* KBID 페이지 헤더 */}
      <div className="bg-white border-b" style={{ borderColor: "var(--kbid-border)", padding: "12px 16px", marginBottom: 14 }}>
        <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--kbid-text-strong)" }}>
          📈 사정률 예측
        </h1>
        <p className="text-[12px] mt-1" style={{ color: "var(--kbid-text-meta)" }}>
          과거 낙찰 데이터 기반 선형회귀 모델 · 95% 신뢰 구간 입찰가 범위 제공
        </p>
      </div>

      <div className="grid grid-cols-[340px_1fr] gap-3">
        {/* 좌측: 공고 선택 */}
        <div>
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
          >
            예측 대상 공고 선택
          </div>
          <div className="bg-white border-x border-b" style={{ borderColor: "var(--kbid-border)" }}>
            {PREDICTION_TARGETS.map((p) => (
              <div
                key={p.id}
                onClick={() => setSelected(p)}
                className="cursor-pointer border-b px-3 py-2.5 hover:bg-blue-50"
                style={{
                  borderColor: "var(--kbid-border)",
                  background: selected.id === p.id ? "#FFF7ED" : undefined,
                  borderLeft: selected.id === p.id ? "3px solid #E8913A" : "3px solid transparent",
                }}
              >
                <div className="text-[13px] font-bold" style={{ color: "var(--kbid-text-strong)" }}>
                  {p.title}
                </div>
                <div className="text-[11px] mt-0.5" style={{ color: "var(--kbid-text-meta)" }}>
                  <span
                    className="inline-block px-1.5 py-0.5 text-[10px] font-bold mr-1"
                    style={{
                      background: p.type === "공사" ? "#DCE8F6" : "#EEDCF6",
                      color: p.type === "공사" ? "#0E47C8" : "#6F2B96",
                      borderRadius: 2,
                    }}
                  >
                    {p.type}
                  </span>
                  {p.area} · {p.budget.toLocaleString()}만원
                </div>
              </div>
            ))}
          </div>

          {/* 예측 입력 피처 */}
          <div className="mt-3">
            <div
              className="text-white px-3 py-2 text-[12px] font-bold"
              style={{ background: "linear-gradient(to bottom, #346081, #1E3A6B)" }}
            >
              예측 입력 피처
            </div>
            <table className="kbid-form-table" style={{ borderTop: "none" }}>
              <tbody>
                <tr>
                  <th style={{ width: 100 }}>업종코드</th>
                  <td>공사/토목</td>
                </tr>
                <tr>
                  <th>예산 규모</th>
                  <td>{selected.budget.toLocaleString()}만원</td>
                </tr>
                <tr>
                  <th>지역</th>
                  <td>{selected.area}</td>
                </tr>
                <tr>
                  <th>발주기관 유형</th>
                  <td>공기업</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* 우측: 예측 결과 */}
        <div>
          {/* 예측 결과 KBID form-table */}
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
          >
            예측 결과
          </div>
          <div className="grid grid-cols-3 border-x border-b" style={{ borderColor: "var(--kbid-border)" }}>
            <div className="border-r p-4" style={{ borderColor: "var(--kbid-border)" }}>
              <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>예상 사정률</div>
              <div className="text-[26px] font-extrabold my-1" style={{ color: "var(--kbid-primary)" }}>
                {selected.predRate}%
              </div>
              <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
                95% CI: {selected.predMin}% ~ {selected.predMax}%
              </div>
            </div>
            <div className="border-r p-4" style={{ borderColor: "var(--kbid-border)" }}>
              <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>권장 입찰가</div>
              <div className="text-[26px] font-extrabold my-1" style={{ color: "#2B8B3C" }}>
                {selected.bidAmountPred.toLocaleString()}
              </div>
              <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
                만원 (범위 {selected.bidMin.toLocaleString()}~{selected.bidMax.toLocaleString()})
              </div>
            </div>
            <div className="p-4">
              <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>예측 신뢰도</div>
              <div className="text-[26px] font-extrabold my-1" style={{ color: "#E8913A" }}>
                {selected.confidence}%
              </div>
              <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
                학습 데이터 기반
              </div>
              <div className="h-1.5 mt-2 overflow-hidden" style={{ background: "#E5E5E5" }}>
                <div
                  style={{
                    width: `${selected.confidence}%`,
                    height: "100%",
                    background: "linear-gradient(to right, #437194, #E8913A)",
                  }}
                />
              </div>
            </div>
          </div>

          {/* 권장 범위 알림 */}
          <div
            className="mt-3 border px-3 py-2 text-[12px]"
            style={{ background: "#FFF7ED", borderColor: "#E8913A", color: "#C56F1A" }}
          >
            ℹ️ 권장 입찰가 범위:{" "}
            <strong>
              {selected.bidMin.toLocaleString()}만원 ~ {selected.bidMax.toLocaleString()}만원
            </strong>{" "}
            (예산 대비 {selected.predMin}% ~ {selected.predMax}%)
          </div>

          {/* 유사 업종 차트 */}
          <div className="mt-3">
            <div
              className="text-white px-3 py-2 text-[12px] font-bold"
              style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
            >
              유사 업종 낙찰 이력 (최근 6개월)
            </div>
            <div className="bg-white border-x border-b p-3" style={{ borderColor: "var(--kbid-border)" }}>
              <AmLineChart data={TREND_DATA} height={240} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
