"use client";

import { useState } from "react";
import {
  ComposedChart, Bar, Line, BarChart, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const TREND_DATA = [
  { month: "10월", construction: 82.4, service: 88.1, total: 85.1 },
  { month: "11월", construction: 80.9, service: 87.3, total: 84.0 },
  { month: "12월", construction: 79.5, service: 89.2, total: 84.2 },
  { month: "1월", construction: 83.1, service: 90.4, total: 86.5 },
  { month: "2월", construction: 81.7, service: 88.8, total: 85.1 },
  { month: "3월", construction: 84.3, service: 91.2, total: 87.6 },
];

const REGION_DATA = [
  { region: "서울", rate: 86.2, count: 342 },
  { region: "경기", rate: 83.7, count: 289 },
  { region: "부산", rate: 81.4, count: 178 },
  { region: "대전", rate: 89.1, count: 134 },
  { region: "인천", rate: 84.5, count: 156 },
  { region: "광주", rate: 82.3, count: 98 },
  { region: "대구", rate: 80.9, count: 112 },
];

const PERIODS = ["1개월", "3개월", "6개월", "1년"];

export default function StatisticsPage() {
  const [activePeriod, setActivePeriod] = useState("6개월");

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl font-extrabold">통계 리포트</h1>
        <p className="text-[13px] text-slate-500 mt-1">
          업종별·지역별 사정률 분포 · 시계열 트렌드 · 리포트 다운로드
        </p>
      </div>

      {/* 필터 바 */}
      <div className="flex items-center gap-2.5 p-3.5 bg-white rounded-[10px] mb-4 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)] flex-wrap">
        <span className="text-[13px] font-semibold text-slate-500">분석 기간:</span>
        {PERIODS.map((p) => (
          <button
            key={p}
            onClick={() => setActivePeriod(p)}
            className={`px-3 py-[5px] rounded-[7px] text-[12.5px] font-semibold border-[1.5px] transition ${
              activePeriod === p
                ? "bg-primary text-white border-primary"
                : "bg-transparent text-slate-500 border-border hover:bg-[#F0F4F8]"
            }`}
          >
            {p}
          </button>
        ))}
        <div className="ml-auto flex gap-2">
          <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[12.5px] font-semibold border-[1.5px] border-border hover:bg-[#F0F4F8] transition">
            📊 PDF 리포트
          </button>
          <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[12.5px] font-semibold border-[1.5px] border-border hover:bg-[#F0F4F8] transition">
            📥 CSV 다운로드
          </button>
        </div>
      </div>

      {/* 차트 그리드 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* 월별 추이 */}
        <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold">사정률 월별 추이</div>
              <div className="text-xs text-slate-500 mt-0.5">공사 vs 용역 비교</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <ComposedChart data={TREND_DATA} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis domain={[75, 95]} tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip formatter={(v: number, n: string) => [`${v}%`, n]} />
              <Bar dataKey="construction" fill="#0066CC" opacity={0.7} name="공사" radius={[3, 3, 0, 0] as any} />
              <Line type="monotone" dataKey="service" stroke="#7C3AED" strokeWidth={2.5} dot={{ r: 4, fill: "#7C3AED" }} name="용역" />
              <Legend iconType="circle" iconSize={8} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 지역별 */}
        <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold">지역별 평균 사정률</div>
              <div className="text-xs text-slate-500 mt-0.5">낙찰 건수 포함</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={REGION_DATA} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#F1F5F9" />
              <XAxis type="number" domain={[75, 95]} tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} tickFormatter={(v: number) => `${v}%`} />
              <YAxis dataKey="region" type="category" tick={{ fontSize: 12, fill: "#475569" }} axisLine={false} tickLine={false} width={36} />
              <Tooltip formatter={(v: number, n: string) => n === "rate" ? [`${v}%`, "사정률"] : [`${v}건`, "건수"]} />
              <Bar dataKey="rate" fill="#0066CC" radius={[0, 4, 4, 0] as any} name="rate" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* 상세 테이블 */}
      <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-bold">지역별 상세 통계</div>
            <div className="text-xs text-slate-500 mt-0.5">최근 6개월 집계 기준</div>
          </div>
        </div>
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">지역</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">평균 사정률</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">낙찰 건수</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">최소 사정률</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">최대 사정률</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">전월 대비</th>
            </tr>
          </thead>
          <tbody>
            {REGION_DATA.map((r, i) => (
              <tr key={r.region} className="hover:bg-[#F8FAFC]">
                <td className="p-[11px_12px] border-b border-border font-semibold">{r.region}</td>
                <td className="p-[11px_12px] border-b border-border">
                  <span className="font-bold text-primary">{r.rate}%</span>
                </td>
                <td className="p-[11px_12px] border-b border-border">{r.count}건</td>
                <td className="p-[11px_12px] border-b border-border text-slate-500">{(r.rate - 4.1).toFixed(1)}%</td>
                <td className="p-[11px_12px] border-b border-border text-slate-500">{(r.rate + 3.8).toFixed(1)}%</td>
                <td className="p-[11px_12px] border-b border-border">
                  <span className={i % 2 === 0 ? "text-green-600" : "text-red-600"}>
                    {i % 2 === 0 ? "↑ +1.2%" : "↓ -0.8%"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
