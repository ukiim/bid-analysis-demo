"use client";

import { useState, useMemo } from "react";
import { formatAmount, formatDate } from "@/lib/utils";

// 데모 데이터
const DEMO_ANNOUNCEMENTS = [
  { id: "A2024-8821", title: "한강변 보행로 정비공사", org: "서울시 한강사업본부", type: "공사", area: "서울", budget: 385000000, deadline: "2026-04-15", rate: 84.2, status: "진행중" },
  { id: "A2024-8820", title: "국방과학연구소 시설유지보수 용역", org: "국방과학연구소", type: "용역", area: "대전", budget: 122000000, deadline: "2026-04-18", rate: 91.5, status: "진행중" },
  { id: "A2024-8819", title: "부산항 항만시설 확장공사", org: "부산항만공사", type: "공사", area: "부산", budget: 1520000000, deadline: "2026-04-20", rate: 78.9, status: "진행중" },
  { id: "A2024-8818", title: "인천공항 2터미널 전기설비 유지보수", org: "인천국제공항공사", type: "용역", area: "인천", budget: 87000000, deadline: "2026-04-22", rate: 88.3, status: "진행중" },
  { id: "A2024-8817", title: "경기도청 청사 리모델링 공사", org: "경기도", type: "공사", area: "경기", budget: 678000000, deadline: "2026-04-25", rate: 82.7, status: "진행중" },
  { id: "A2024-8816", title: "육군 제37사단 막사 신축공사", org: "육군본부", type: "공사", area: "강원", budget: 893000000, deadline: "2026-04-28", rate: 80.1, status: "진행중" },
  { id: "A2024-8815", title: "부산시 도시철도 3호선 유지보수 용역", org: "부산교통공사", type: "용역", area: "부산", budget: 234000000, deadline: "2026-05-02", rate: 89.7, status: "진행중" },
  { id: "A2024-8814", title: "세종시 스마트시티 통합플랫폼 구축", org: "세종특별자치시", type: "용역", area: "세종", budget: 456000000, deadline: "2026-05-05", rate: 86.4, status: "진행중" },
];

const KPI_DATA = [
  { label: "오늘 수집 공고", value: "436건", change: "+12.4%", up: true },
  { label: "공사 공고", value: "248건", change: "+8.1%", up: true },
  { label: "용역 공고", value: "188건", change: "+18.3%", up: true },
  { label: "국방부 공고", value: "89건", change: "-2.1%", up: false },
];

export default function AnnouncementsPage() {
  const [filter, setFilter] = useState({ type: "all", area: "all", search: "" });

  const filtered = useMemo(() => {
    return DEMO_ANNOUNCEMENTS.filter((a) => {
      if (filter.type !== "all" && a.type !== filter.type) return false;
      if (filter.area !== "all" && a.area !== filter.area) return false;
      if (filter.search && !a.title.includes(filter.search) && !a.org.includes(filter.search)) return false;
      return true;
    });
  }, [filter]);

  return (
    <div>
      {/* 페이지 헤더 */}
      <div className="mb-5">
        <h1 className="text-xl font-extrabold">공고 통합 조회</h1>
        <p className="text-[13px] text-slate-500 mt-1">
          나라장터 + 국방부 OpenAPI 통합 수집 · 업종/지역/기간 다차원 필터
        </p>
      </div>

      {/* KPI 카드 */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        {KPI_DATA.map((k, i) => (
          <div key={i} className="bg-white rounded-[10px] p-[18px_20px] shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
            <div className="text-xs text-slate-500 font-medium mb-1.5">{k.label}</div>
            <div className="text-2xl font-extrabold">{k.value}</div>
            <div className={`text-xs mt-1 ${k.up ? "text-green-600" : "text-red-600"}`}>
              {k.up ? "↑" : "↓"} 전일 대비 {k.change}
            </div>
          </div>
        ))}
      </div>

      {/* 필터 바 */}
      <div className="flex items-center gap-2.5 p-3.5 bg-white rounded-[10px] mb-4 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)] flex-wrap">
        <input
          className="flex-1 min-w-[200px] py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] outline-none focus:border-primary"
          placeholder="🔍  공고명, 발주기관 검색"
          value={filter.search}
          onChange={(e) => setFilter((f) => ({ ...f, search: e.target.value }))}
        />
        <select
          className="py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer"
          value={filter.type}
          onChange={(e) => setFilter((f) => ({ ...f, type: e.target.value }))}
        >
          <option value="all">전체 유형</option>
          <option value="공사">공사</option>
          <option value="용역">용역</option>
        </select>
        <select
          className="py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer"
          value={filter.area}
          onChange={(e) => setFilter((f) => ({ ...f, area: e.target.value }))}
        >
          <option value="all">전체 지역</option>
          {["서울", "경기", "부산", "대전", "인천", "강원", "세종"].map((a) => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>
        <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[13px] font-semibold bg-primary text-white hover:bg-primary-dark transition">
          필터 적용
        </button>
      </div>

      {/* 테이블 */}
      <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-bold">공고 목록</div>
            <div className="text-xs text-slate-500 mt-0.5">총 {filtered.length}건 조회됨</div>
          </div>
          <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[13px] font-semibold border-[1.5px] border-border hover:bg-[#F0F4F8] transition">
            📥 CSV 다운로드
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">공고번호</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">공고명</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">발주기관</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">유형</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">지역</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">예산</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">마감일</th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">예상사정률</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((a) => (
                <tr key={a.id} className="hover:bg-[#F8FAFC]">
                  <td className="p-[11px_12px] border-b border-border font-mono text-xs text-slate-500">{a.id}</td>
                  <td className="p-[11px_12px] border-b border-border font-semibold max-w-[220px]">{a.title}</td>
                  <td className="p-[11px_12px] border-b border-border text-[12.5px] text-slate-500">{a.org}</td>
                  <td className="p-[11px_12px] border-b border-border">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                      a.type === "공사" ? "bg-blue-50 text-blue-600" : "bg-purple-50 text-purple-600"
                    }`}>
                      {a.type}
                    </span>
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-[13px]">{a.area}</td>
                  <td className="p-[11px_12px] border-b border-border font-bold text-right">{formatAmount(a.budget)}</td>
                  <td className="p-[11px_12px] border-b border-border text-[12.5px] text-slate-500">{a.deadline}</td>
                  <td className="p-[11px_12px] border-b border-border">
                    <div className="flex items-center gap-1.5">
                      <div className="w-[60px] h-1.5 rounded-full bg-slate-200 overflow-hidden">
                        <div className="h-full rounded-full bg-primary" style={{ width: `${a.rate}%` }} />
                      </div>
                      <span className="font-bold text-primary text-[13px]">{a.rate}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
