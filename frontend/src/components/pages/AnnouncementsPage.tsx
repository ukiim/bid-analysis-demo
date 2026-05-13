"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";

interface AnnouncementRow {
  id: string;
  bid_number: string;
  title: string;
  org: string;
  parent_org: string | null;
  type: string;
  area: string | null;
  budget: number | null;
  estimated_price: number | null;
  license_category: string | null;
  deadline: string | null;
  opening_at: string | null;
  site_visit_at: string | null;
  rate: number | null;
  first_place_rate: number | null;
  status: string;
  source: string;
}

interface RegionMeta {
  sido: string;
  sigungu_list: string[];
  count: number;
}

interface LicenseMeta {
  value: string;
  count: number;
}

const KPI_DATA = [
  { label: "오늘 수집 공고", value: "436건", change: "+12.4%", up: true },
  { label: "공사 공고", value: "248건", change: "+8.1%", up: true },
  { label: "용역 공고", value: "188건", change: "+18.3%", up: true },
  { label: "국방부 공고", value: "89건", change: "-2.1%", up: false },
];

function formatBudget(n: number | null): string {
  if (n == null) return "-";
  if (n >= 1e8) return `${(n / 1e8).toFixed(1)}억`;
  if (n >= 1e4) return `${(n / 1e4).toFixed(0)}만`;
  return n.toLocaleString();
}

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function AnnouncementsPage() {
  const [filter, setFilter] = useState({
    type: "all",
    region_sido: "all",
    region_sigungu: "all",
    license_category: "all",
    keyword: "",
    date_from: "",
    date_to: "",
    first_only: false,
  });
  const [items, setItems] = useState<AnnouncementRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [regions, setRegions] = useState<RegionMeta[]>([]);
  const [licenseCategories, setLicenseCategories] = useState<LicenseMeta[]>([]);

  // 메타 로드 (1회)
  useEffect(() => {
    fetch(`/api/v1/announcements/meta/regions`, { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d) {
          setRegions(d.regions ?? []);
          setLicenseCategories(d.license_categories ?? []);
        }
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = new URLSearchParams({ page: "1", page_size: "20" });
    if (filter.type !== "all") params.set("category", filter.type);
    if (filter.region_sido !== "all") params.set("region_sido", filter.region_sido);
    if (filter.region_sigungu !== "all") params.set("region_sigungu", filter.region_sigungu);
    if (filter.license_category !== "all")
      params.set("license_category", filter.license_category);
    if (filter.keyword) params.set("keyword", filter.keyword);
    if (filter.date_from) params.set("date_from", filter.date_from);
    if (filter.date_to) params.set("date_to", filter.date_to);

    fetch(`/api/v1/announcements?${params.toString()}`, {
      headers: authHeaders(),
    })
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => {
        if (cancelled) return;
        setItems(d.items ?? []);
        setTotal(d.total ?? 0);
        setLoading(false);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "공고 조회 실패");
        setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    filter.type,
    filter.region_sido,
    filter.region_sigungu,
    filter.license_category,
    filter.keyword,
    filter.date_from,
    filter.date_to,
  ]);

  const visible = useMemo(() => {
    return items.filter((a) => {
      if (filter.first_only && a.first_place_rate == null) return false;
      return true;
    });
  }, [items, filter.first_only]);

  const sigunguOptions = useMemo(() => {
    if (filter.region_sido === "all") return [];
    const r = regions.find((x) => x.sido === filter.region_sido);
    return r?.sigungu_list ?? [];
  }, [filter.region_sido, regions]);

  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl font-extrabold">공고 통합 조회</h1>
        <p className="text-[13px] text-slate-500 mt-1">
          나라장터 + 국방부 OpenAPI 통합 수집 · 업종/지역/기간 다차원 필터 (KBID 동등성)
        </p>
      </div>

      <div className="grid grid-cols-4 gap-4 mb-4">
        {KPI_DATA.map((k, i) => (
          <div
            key={i}
            className="bg-white rounded-[10px] p-[18px_20px] shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]"
          >
            <div className="text-xs text-slate-500 font-medium mb-1.5">{k.label}</div>
            <div className="text-2xl font-extrabold">{k.value}</div>
            <div className={`text-xs mt-1 ${k.up ? "text-green-600" : "text-red-600"}`}>
              {k.up ? "↑" : "↓"} 전일 대비 {k.change}
            </div>
          </div>
        ))}
      </div>

      {/* 필터 패널 — KBID 동등성 */}
      <div className="bg-white rounded-[10px] mb-4 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
        <div className="grid grid-cols-12 gap-2.5 p-3.5">
          {/* 1행: 검색 + 카테고리 */}
          <input
            className="col-span-5 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] outline-none focus:border-primary"
            placeholder="🔍  공고명, 발주기관 검색"
            value={filter.keyword}
            onChange={(e) => setFilter((f) => ({ ...f, keyword: e.target.value }))}
          />
          <select
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer"
            value={filter.type}
            onChange={(e) => setFilter((f) => ({ ...f, type: e.target.value }))}
          >
            <option value="all">전체 카테고리</option>
            <option value="공사">공사</option>
            <option value="용역">용역</option>
            <option value="물품">물품</option>
            <option value="구매">구매</option>
          </select>
          <select
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer"
            value={filter.license_category}
            onChange={(e) => setFilter((f) => ({ ...f, license_category: e.target.value }))}
          >
            <option value="all">전체 업종면허</option>
            {licenseCategories.map((lc) => (
              <option key={lc.value} value={lc.value}>
                {lc.value} ({lc.count})
              </option>
            ))}
          </select>
          <button
            onClick={() =>
              setFilter((f) => ({ ...f, first_only: !f.first_only }))
            }
            className={`col-span-3 inline-flex items-center justify-center gap-1.5 py-[7px] rounded-[7px] text-[13px] font-semibold transition border-[1.5px] ${
              filter.first_only
                ? "bg-[#E8913A] text-white border-[#E8913A]"
                : "bg-white text-slate-700 border-border hover:bg-[#FFF7ED]"
            }`}
            title="과거 1순위 낙찰률이 기록된 공고만 표시"
          >
            ★ 1순위만
          </button>

          {/* 2행: 시도 + 시군구 + 날짜 범위 */}
          <select
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer"
            value={filter.region_sido}
            onChange={(e) =>
              setFilter((f) => ({
                ...f,
                region_sido: e.target.value,
                region_sigungu: "all",
              }))
            }
          >
            <option value="all">전체 시·도</option>
            {regions.map((r) => (
              <option key={r.sido} value={r.sido}>
                {r.sido} ({r.count})
              </option>
            ))}
          </select>
          <select
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px] bg-[#F0F4F8] cursor-pointer disabled:opacity-50"
            value={filter.region_sigungu}
            onChange={(e) =>
              setFilter((f) => ({ ...f, region_sigungu: e.target.value }))
            }
            disabled={sigunguOptions.length === 0}
          >
            <option value="all">
              {sigunguOptions.length === 0 ? "시·군·구 없음" : "전체 시·군·구"}
            </option>
            {sigunguOptions.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <span className="col-span-1 flex items-center text-[12px] text-slate-500 justify-end pr-1">
            공고기간
          </span>
          <input
            type="date"
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px]"
            value={filter.date_from}
            onChange={(e) => setFilter((f) => ({ ...f, date_from: e.target.value }))}
          />
          <span className="col-span-1 flex items-center justify-center text-[12px] text-slate-500">
            ~
          </span>
          <input
            type="date"
            className="col-span-2 py-[7px] px-3 border-[1.5px] border-border rounded-[7px] text-[13px]"
            value={filter.date_to}
            onChange={(e) => setFilter((f) => ({ ...f, date_to: e.target.value }))}
          />
          <button
            onClick={() =>
              setFilter({
                type: "all",
                region_sido: "all",
                region_sigungu: "all",
                license_category: "all",
                keyword: "",
                date_from: "",
                date_to: "",
                first_only: false,
              })
            }
            className="col-span-2 py-[7px] rounded-[7px] text-[13px] font-semibold border-[1.5px] border-border hover:bg-slate-50"
          >
            필터 초기화
          </button>
        </div>
      </div>

      <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
        <div className="flex items-center justify-between mb-4">
          <div>
            <div className="text-sm font-bold">공고 목록</div>
            <div className="text-xs text-slate-500 mt-0.5">
              {loading
                ? "조회 중..."
                : `${visible.length}건 표시 / 총 ${total.toLocaleString()}건`}
            </div>
          </div>
          <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[13px] font-semibold border-[1.5px] border-border hover:bg-[#F0F4F8] transition">
            📥 CSV 다운로드
          </button>
        </div>

        {error && (
          <div className="p-3 mb-3 bg-red-50 border border-red-200 text-red-700 text-[13px] rounded">
            {error}
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px] min-w-[1400px]">
            <thead>
              <tr>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  공고명 / 공고번호
                </th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  업종면허 / 지역
                </th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  공고기관 / 수요기관
                </th>
                <th className="text-right p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  기초금액 / 추정가격
                </th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  투찰마감
                </th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  개찰일시
                </th>
                <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  현설일
                </th>
                <th className="text-center p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  유형
                </th>
                <th className="text-center p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  사정률 / 1순위
                </th>
                <th className="text-center p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">
                  분석
                </th>
              </tr>
            </thead>
            <tbody>
              {loading && (
                <tr>
                  <td colSpan={10} className="p-6 text-center text-slate-400">
                    공고 데이터 로딩 중...
                  </td>
                </tr>
              )}
              {!loading && visible.length === 0 && (
                <tr>
                  <td colSpan={10} className="p-6 text-center text-slate-400">
                    조건에 맞는 공고가 없습니다
                  </td>
                </tr>
              )}
              {visible.map((a) => (
                <tr key={a.id} className="hover:bg-[#F8FAFC]">
                  <td className="p-[11px_12px] border-b border-border max-w-[340px]">
                    <div className="font-semibold truncate">{a.title}</div>
                    <div className="text-[11px] text-slate-400 font-mono">
                      {a.bid_number}
                    </div>
                  </td>
                  <td className="p-[11px_12px] border-b border-border">
                    <div className="text-[12.5px]">{a.license_category ?? "-"}</div>
                    <div className="text-[11px] text-slate-500">{a.area ?? "-"}</div>
                  </td>
                  <td className="p-[11px_12px] border-b border-border max-w-[200px]">
                    <div className="text-[12.5px] truncate">{a.org}</div>
                    <div className="text-[11px] text-slate-500 truncate">
                      {a.parent_org && a.parent_org !== a.org ? a.parent_org : ""}
                    </div>
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-right">
                    <div className="font-bold text-[12.5px]">
                      {formatBudget(a.budget)}
                    </div>
                    <div className="text-[11px] text-slate-500">
                      {a.estimated_price ? formatBudget(a.estimated_price) : "-"}
                    </div>
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-[12px] text-slate-600">
                    {a.deadline ?? "-"}
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-[12px] text-slate-600">
                    {a.opening_at ?? "-"}
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-[12px] text-slate-600">
                    {a.site_visit_at ?? "-"}
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-center">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-semibold ${
                        a.type === "공사"
                          ? "bg-blue-50 text-blue-600"
                          : a.type === "용역"
                          ? "bg-purple-50 text-purple-600"
                          : "bg-slate-50 text-slate-600"
                      }`}
                    >
                      {a.type}
                    </span>
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-center">
                    {a.rate != null ? (
                      <div className="font-bold text-primary text-[12.5px]">
                        {a.rate.toFixed(2)}%
                      </div>
                    ) : (
                      <div className="text-slate-300 text-[12px]">-</div>
                    )}
                    {a.first_place_rate != null ? (
                      <div className="font-bold text-[#3358A4] text-[11px]">
                        1순위 {a.first_place_rate.toFixed(2)}%
                      </div>
                    ) : (
                      <div className="text-slate-300 text-[11px]">-</div>
                    )}
                  </td>
                  <td className="p-[11px_12px] border-b border-border text-center">
                    <Link
                      href={`/analysis/${a.id}`}
                      className="inline-flex items-center gap-1 px-3 py-1 rounded text-[11px] font-semibold bg-[#3358A4] text-white hover:bg-[#2C4F8A] transition"
                    >
                      분석
                    </Link>
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
