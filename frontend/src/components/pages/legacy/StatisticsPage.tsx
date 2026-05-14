"use client";

/**
 * 통계 리포트 페이지 — v4 KBID 톤
 */
import { useState } from "react";
import AmLineChart from "@/components/charts/AmLineChart";

const TREND_DATA = [
  { period: "10월", avg_rate: 85.1, min_rate: 82.4, max_rate: 88.1 },
  { period: "11월", avg_rate: 84.0, min_rate: 80.9, max_rate: 87.3 },
  { period: "12월", avg_rate: 84.2, min_rate: 79.5, max_rate: 89.2 },
  { period: "1월", avg_rate: 86.5, min_rate: 83.1, max_rate: 90.4 },
  { period: "2월", avg_rate: 85.1, min_rate: 81.7, max_rate: 88.8 },
  { period: "3월", avg_rate: 87.6, min_rate: 84.3, max_rate: 91.2 },
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
      {/* KBID 페이지 헤더 */}
      <div
        className="bg-white border-b"
        style={{ borderColor: "var(--kbid-border)", padding: "12px 16px", marginBottom: 14 }}
      >
        <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--kbid-text-strong)" }}>
          📊 통계 리포트
        </h1>
        <p className="text-[12px] mt-1" style={{ color: "var(--kbid-text-meta)" }}>
          업종별·지역별 사정률 분포 · 시계열 트렌드 · 리포트 다운로드
        </p>
      </div>

      {/* 필터 행 — KBID form-table 톤 */}
      <table className="kbid-form-table mb-3">
        <tbody>
          <tr>
            <th style={{ width: 110 }}>분석 기간</th>
            <td>
              <div className="flex items-center gap-1.5">
                {PERIODS.map((p) => (
                  <button
                    key={p}
                    onClick={() => setActivePeriod(p)}
                    className={`kbid-btn-quick ${activePeriod === p ? "active" : ""}`}
                  >
                    {p}
                  </button>
                ))}
                <div className="flex-1" />
                <button className="kbid-btn-secondary">📊 PDF 리포트</button>
                <button className="kbid-btn-secondary">📥 CSV 다운로드</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      {/* 차트 그리드 */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {/* 월별 추이 */}
        <div>
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "var(--text)" }}
          >
            사정률 월별 추이 (평균/최저/최고)
          </div>
          <div className="bg-white border-x border-b p-3" style={{ borderColor: "var(--kbid-border)" }}>
            <AmLineChart data={TREND_DATA} height={240} />
          </div>
        </div>

        {/* 지역별 평균 사정률 (가로 바 차트 — KBID 톤 단순 CSS) */}
        <div>
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "var(--text)" }}
          >
            지역별 평균 사정률
          </div>
          <div className="bg-white border-x border-b p-4" style={{ borderColor: "var(--kbid-border)" }}>
            <div className="space-y-2">
              {REGION_DATA.map((r) => {
                const max = Math.max(...REGION_DATA.map((d) => d.rate));
                const pct = (r.rate / max) * 100;
                return (
                  <div key={r.region} className="flex items-center gap-2 text-[12px]">
                    <div className="w-12 font-bold text-right" style={{ color: "var(--kbid-text-strong)" }}>
                      {r.region}
                    </div>
                    <div className="flex-1 h-6 relative" style={{ background: "#F4F7FA", border: "1px solid var(--kbid-border)" }}>
                      <div
                        style={{
                          width: `${pct}%`,
                          height: "100%",
                          background: "var(--accent)",
                        }}
                      />
                      <div
                        className="absolute inset-0 flex items-center px-2 font-bold text-white"
                        style={{ fontSize: 11 }}
                      >
                        {r.rate}% <span className="ml-auto text-[10px] opacity-90">{r.count}건</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* 상세 테이블 */}
      <div>
        <div
          className="text-white px-3 py-2 text-[12px] font-bold"
          style={{ background: "var(--text)" }}
        >
          지역별 상세 통계 — 최근 {activePeriod} 집계
        </div>
        <table className="kbid-list-table" style={{ borderTop: "none" }}>
          <thead>
            <tr>
              <th style={{ width: 70 }}>지역</th>
              <th>평균 사정률</th>
              <th>낙찰 건수</th>
              <th>최소 사정률</th>
              <th>최대 사정률</th>
              <th>전월 대비</th>
            </tr>
          </thead>
          <tbody>
            {REGION_DATA.map((r, i) => (
              <tr key={r.region}>
                <td style={{ fontWeight: 700 }}>{r.region}</td>
                <td>
                  <span style={{ fontWeight: 700, color: "var(--kbid-primary)" }}>
                    {r.rate}%
                  </span>
                </td>
                <td>{r.count}건</td>
                <td style={{ color: "#666" }}>{(r.rate - 4.1).toFixed(1)}%</td>
                <td style={{ color: "#666" }}>{(r.rate + 3.8).toFixed(1)}%</td>
                <td>
                  <span
                    style={{
                      color: i % 2 === 0 ? "#2B8B3C" : "#D9342B",
                      fontWeight: 600,
                    }}
                  >
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
