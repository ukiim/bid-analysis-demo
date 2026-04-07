"use client";

import { useState } from "react";
import {
  ComposedChart, Area, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";

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
  { month: "10월", construction: 82.4, service: 88.1 },
  { month: "11월", construction: 80.9, service: 87.3 },
  { month: "12월", construction: 79.5, service: 89.2 },
  { month: "1월", construction: 83.1, service: 90.4 },
  { month: "2월", construction: 81.7, service: 88.8 },
  { month: "3월", construction: 84.3, service: 91.2 },
];

const FEATURES = [
  ["업종코드", "공사/토목"],
  ["예산 규모", ""],
  ["지역", ""],
  ["발주기관 유형", "공기업"],
];

export default function PredictionPage() {
  const [selected, setSelected] = useState(PREDICTION_TARGETS[0]);

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl font-extrabold">사정률 예측</h1>
        <p className="text-[13px] text-slate-500 mt-1">
          과거 낙찰 데이터 기반 선형회귀 모델 · 95% 신뢰 구간 입찰가 범위 제공
        </p>
      </div>

      <div className="grid grid-cols-[340px_1fr] gap-4 mb-4">
        {/* 좌측: 공고 선택 */}
        <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)] h-fit">
          <div className="text-sm font-bold mb-3">예측 대상 공고 선택</div>
          {PREDICTION_TARGETS.map((p) => (
            <div
              key={p.id}
              onClick={() => setSelected(p)}
              className={`p-3 border-2 rounded-lg cursor-pointer mb-2 transition ${
                selected.id === p.id
                  ? "border-primary bg-blue-50"
                  : "border-border hover:border-slate-300"
              }`}
            >
              <div className="text-[13px] font-bold">{p.title}</div>
              <div className="text-[11.5px] text-slate-500 mt-0.5">
                {p.area} · {p.type} · {p.budget.toLocaleString()}만원
              </div>
            </div>
          ))}

          <div className="h-px bg-border my-4" />

          <div className="text-[13px] font-bold mb-2.5">예측 입력 피처</div>
          {FEATURES.map(([k, v]) => (
            <div key={k} className="flex justify-between items-center text-[12.5px] py-[5px] border-b border-border">
              <span className="text-slate-500">{k}</span>
              <span className="font-semibold">
                {k === "예산 규모" ? `${selected.budget.toLocaleString()}만원` : k === "지역" ? selected.area : v}
              </span>
            </div>
          ))}
        </div>

        {/* 우측: 예측 결과 */}
        <div>
          <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)] mb-4">
            <div className="text-sm font-bold mb-4">예측 결과</div>

            <div className="grid grid-cols-3 gap-3 mb-4">
              <div className="p-3.5 bg-[#F8FAFC] rounded-lg text-center">
                <div className="text-[11px] text-slate-500 font-medium">예상 사정률</div>
                <div className="text-[22px] font-extrabold text-primary my-1">{selected.predRate}%</div>
                <div className="text-[11px] text-slate-500">95% CI: {selected.predMin}% ~ {selected.predMax}%</div>
              </div>
              <div className="p-3.5 bg-[#F8FAFC] rounded-lg text-center">
                <div className="text-[11px] text-slate-500 font-medium">권장 입찰가</div>
                <div className="text-[22px] font-extrabold text-green-600 my-1">{selected.bidAmountPred.toLocaleString()}</div>
                <div className="text-[11px] text-slate-500">만원</div>
              </div>
              <div className="p-3.5 bg-[#F8FAFC] rounded-lg text-center">
                <div className="text-[11px] text-slate-500 font-medium">예측 신뢰도</div>
                <div className="text-[22px] font-extrabold text-amber-600 my-1">{selected.confidence}%</div>
                <div className="text-[11px] text-slate-500">학습 데이터 기반</div>
              </div>
            </div>

            {/* 알림 */}
            <div className="p-3 rounded-lg bg-blue-50 text-blue-700 border border-blue-200 text-[13px] flex items-start gap-2 mb-3">
              <span>ℹ️</span>
              <span>
                권장 입찰가 범위: <strong>{selected.bidMin.toLocaleString()}만원 ~ {selected.bidMax.toLocaleString()}만원</strong>
                {" "}(예산 대비 {selected.predMin}% ~ {selected.predMax}%)
              </span>
            </div>

            {/* 신뢰도 바 */}
            <div className="text-[12.5px] text-slate-500 mb-1.5">예측 신뢰도</div>
            <div className="h-1.5 rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full rounded-full bg-gradient-to-r from-primary to-accent"
                style={{ width: `${selected.confidence}%` }}
              />
            </div>
          </div>

          {/* 유사 업종 차트 */}
          <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
            <div className="text-sm font-bold mb-3.5">유사 업종 낙찰 이력 (최근 6개월)</div>
            <ResponsiveContainer width="100%" height={200}>
              <ComposedChart data={TREND_DATA} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
                <YAxis domain={[75, 95]} tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
                <Tooltip formatter={(v: number, n: string) => [`${v}%`, n === "construction" ? "공사" : "용역"]} />
                <Area type="monotone" dataKey="construction" fill="#EFF6FF" stroke="#0066CC" strokeWidth={2} fillOpacity={0.4} name="construction" />
                <Line type="monotone" dataKey="service" stroke="#7C3AED" strokeWidth={2} dot={{ r: 3 }} name="service" />
                <Legend formatter={(v: string) => (v === "construction" ? "공사 사정률" : "용역 사정률")} iconType="circle" iconSize={8} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  );
}
