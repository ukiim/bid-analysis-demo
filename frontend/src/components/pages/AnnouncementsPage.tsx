"use client";

/**
 * 공고화면 — KBID 입찰사이트 동등 UI (v3)
 *
 * 구조:
 *  1. 4-탭 (법령공고/결과공고/지사공고/전체공고) — KBID 상단 카테고리
 *  2. 6-행 form-table 검색 패널 (카테고리/기간/공고명/기관/도서면적/수집구분)
 *  3. 좌하단 검색약관 안내
 *  4. 14-컬럼 분리 리스트
 *  5. 페이지네이션 + 단위씩 조회
 *
 * KBID 캡쳐(1차 데모 검토 PDF 1페이지) 동등.
 */
import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import KbidTabBar from "@/components/kbid/KbidTabBar";
import KbidFormTable from "@/components/kbid/KbidFormTable";
import KbidPager from "@/components/kbid/KbidPager";

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

type NoticeTab = "law" | "result" | "branch" | "all";

const NOTICE_TABS = [
  { key: "law" as const, label: "법령공고" },
  { key: "result" as const, label: "결과공고" },
  { key: "branch" as const, label: "지사공고" },
  { key: "all" as const, label: "전체공고" },
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

function quickRangeDates(months: number): { from: string; to: string } {
  const to = new Date();
  const from = new Date();
  from.setMonth(from.getMonth() - months);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { from: fmt(from), to: fmt(to) };
}

export default function AnnouncementsPage() {
  const [tab, setTab] = useState<NoticeTab>("all");
  const [filter, setFilter] = useState({
    // 기본값: 공사+용역 (입찰 분석 핵심 카테고리)
    type: "공사,용역",
    region_sido: "all",
    region_sigungu: "all",
    license_category: "all",
    keyword: "",
    org_search: "",
    date_from: "",
    date_to: "",
    area_min: "",
    area_max: "",
    source: "all",
  });
  const [items, setItems] = useState<AnnouncementRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
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
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    });
    if (filter.type !== "all") params.set("category", filter.type);
    if (filter.region_sido !== "all") params.set("region_sido", filter.region_sido);
    if (filter.region_sigungu !== "all")
      params.set("region_sigungu", filter.region_sigungu);
    if (filter.license_category !== "all")
      params.set("license_category", filter.license_category);
    if (filter.keyword) params.set("keyword", filter.keyword);
    if (filter.date_from) params.set("date_from", filter.date_from);
    if (filter.date_to) params.set("date_to", filter.date_to);
    if (filter.source !== "all") params.set("source", filter.source);
    // 4-탭 매핑 — status 또는 source 로 표현
    if (tab === "law") params.set("status", "진행중");
    else if (tab === "result") params.set("status", "낙찰");
    else if (tab === "branch") params.set("source", "D2B");

    fetch(`/api/v1/announcements?${params.toString()}`, { headers: authHeaders() })
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
  }, [tab, page, pageSize, filter]);

  const sigunguOptions = useMemo(() => {
    if (filter.region_sido === "all") return [];
    const r = regions.find((x) => x.sido === filter.region_sido);
    return r?.sigungu_list ?? [];
  }, [filter.region_sido, regions]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const setRange = (months: number) => {
    const { from, to } = quickRangeDates(months);
    setFilter((f) => ({ ...f, date_from: from, date_to: to }));
  };

  return (
    <div>
      {/* 상단 KBID 4-탭 */}
      <KbidTabBar
        items={NOTICE_TABS}
        activeKey={tab}
        onChange={(k) => {
          setTab(k);
          setPage(1);
        }}
      />

      {/* 6-행 form-table */}
      <div className="bg-white">
        <KbidFormTable
          columns={4}
          rows={[
            [
              {
                label: "카테고리",
                content: (
                  <select
                    value={filter.type}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, type: e.target.value }))
                    }
                  >
                    <option value="공사,용역">공사 + 용역 (기본)</option>
                    <option value="공사">공사입찰만</option>
                    <option value="용역">용역입찰만</option>
                    <option value="all">전체 카테고리</option>
                  </select>
                ),
              },
              {
                label: "수집구분",
                content: (
                  <select
                    value={filter.source}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, source: e.target.value }))
                    }
                  >
                    <option value="all">전체 출처</option>
                    <option value="G2B">나라장터(G2B)</option>
                    <option value="D2B">국방부(D2B)</option>
                  </select>
                ),
              },
            ],
            [
              {
                label: "기간",
                colSpan: 3,
                content: (
                  <div className="flex items-center gap-2 flex-wrap">
                    <select className="text-[12px]">
                      <option>입찰일</option>
                      <option>공고일</option>
                      <option>개찰일</option>
                    </select>
                    <input
                      type="date"
                      value={filter.date_from}
                      onChange={(e) =>
                        setFilter((f) => ({ ...f, date_from: e.target.value }))
                      }
                    />
                    <span className="text-[12px]">~</span>
                    <input
                      type="date"
                      value={filter.date_to}
                      onChange={(e) =>
                        setFilter((f) => ({ ...f, date_to: e.target.value }))
                      }
                    />
                    <button className="kbid-btn-quick" onClick={() => setRange(0.25)}>1주</button>
                    <button className="kbid-btn-quick" onClick={() => setRange(1)}>1개월</button>
                    <button className="kbid-btn-quick" onClick={() => setRange(3)}>3개월</button>
                    <button className="kbid-btn-quick" onClick={() => setRange(6)}>6개월</button>
                    <button className="kbid-btn-quick" onClick={() => setRange(12)}>1년</button>
                  </div>
                ),
              },
            ],
            [
              {
                label: "공고명",
                colSpan: 3,
                content: (
                  <input
                    type="text"
                    style={{ width: "100%" }}
                    placeholder="공고명 또는 공고번호 일부 입력"
                    value={filter.keyword}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, keyword: e.target.value }))
                    }
                  />
                ),
              },
            ],
            [
              {
                label: "기관",
                colSpan: 3,
                content: (
                  <input
                    type="text"
                    style={{ width: "100%" }}
                    placeholder="공고기관 또는 수요기관"
                    value={filter.org_search}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, org_search: e.target.value }))
                    }
                  />
                ),
              },
            ],
            [
              {
                label: "지역",
                content: (
                  <select
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
                ),
              },
              {
                label: "시·군·구",
                content: (
                  <select
                    value={filter.region_sigungu}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, region_sigungu: e.target.value }))
                    }
                    disabled={sigunguOptions.length === 0}
                  >
                    <option value="all">
                      {sigunguOptions.length === 0 ? "시·군·구 데이터 없음" : "전체"}
                    </option>
                    {sigunguOptions.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                ),
              },
            ],
            [
              {
                label: "업종/면허",
                content: (
                  <select
                    value={filter.license_category}
                    onChange={(e) =>
                      setFilter((f) => ({ ...f, license_category: e.target.value }))
                    }
                  >
                    <option value="all">전체 업종면허</option>
                    {licenseCategories.map((lc) => (
                      <option key={lc.value} value={lc.value}>
                        {lc.value} ({lc.count})
                      </option>
                    ))}
                  </select>
                ),
              },
              {
                label: "도서면적",
                content: (
                  <div className="flex items-center gap-1.5">
                    <input
                      type="number"
                      style={{ width: 80 }}
                      placeholder="최소"
                      value={filter.area_min}
                      onChange={(e) =>
                        setFilter((f) => ({ ...f, area_min: e.target.value }))
                      }
                    />
                    <span className="text-[12px]">~</span>
                    <input
                      type="number"
                      style={{ width: 80 }}
                      placeholder="최대"
                      value={filter.area_max}
                      onChange={(e) =>
                        setFilter((f) => ({ ...f, area_max: e.target.value }))
                      }
                    />
                    <span className="text-[11px] text-gray-500">㎡</span>
                  </div>
                ),
              },
            ],
          ]}
        />

        {/* 검색 버튼 행 */}
        <div
          className="flex items-center justify-between"
          style={{
            padding: "10px 12px",
            background: "var(--kbid-panel-bg)",
            borderLeft: "1px solid var(--kbid-border)",
            borderRight: "1px solid var(--kbid-border)",
            borderBottom: "1px solid var(--kbid-border)",
          }}
        >
          <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
            검색약관: 공고명 또는 공고번호로 부분 일치 검색 · 동일 기간 입찰 결과 통합 조회
          </div>
          <div className="flex items-center gap-2">
            <button
              className="kbid-btn-secondary"
              onClick={() =>
                setFilter({
                  type: "all",
                  region_sido: "all",
                  region_sigungu: "all",
                  license_category: "all",
                  keyword: "",
                  org_search: "",
                  date_from: "",
                  date_to: "",
                  area_min: "",
                  area_max: "",
                  source: "all",
                })
              }
            >
              초기화
            </button>
            <button
              className="kbid-btn-primary"
              onClick={() => setPage(1)}
              style={{ minWidth: 90 }}
            >
              🔍 검 색
            </button>
          </div>
        </div>
      </div>

      {/* 결과 헤더 */}
      <div className="mt-4 mb-2 flex items-center justify-between">
        <div className="text-[13px]">
          <span className="font-bold" style={{ color: "var(--kbid-text-strong)" }}>
            공고 목록
          </span>
          <span className="ml-2 text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
            {loading
              ? "조회 중..."
              : `총 ${total.toLocaleString()}건 · ${page}/${totalPages} 페이지`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <button className="kbid-btn-secondary">📥 엑셀 출력</button>
          <button className="kbid-btn-secondary">🖨 인쇄</button>
        </div>
      </div>

      {error && (
        <div className="mb-2 px-3 py-2 text-[12px] border" style={{ borderColor: "var(--kbid-accent-red)", color: "var(--kbid-accent-red)" }}>
          {error}
        </div>
      )}

      {/* 14-컬럼 분리 리스트 */}
      <div className="overflow-x-auto" style={{ borderTop: "2px solid var(--kbid-primary)" }}>
        <table className="kbid-list-table" style={{ minWidth: 1500 }}>
          <thead>
            <tr>
              <th style={{ width: 44 }}>번호</th>
              <th>공고명</th>
              <th style={{ width: 90 }}>공고번호</th>
              <th style={{ width: 70 }}>업종</th>
              <th style={{ width: 70 }}>면허</th>
              <th style={{ width: 70 }}>지역</th>
              <th style={{ width: 140 }}>공고기관</th>
              <th style={{ width: 110 }}>수요기관</th>
              <th style={{ width: 100 }}>기초금액</th>
              <th style={{ width: 100 }}>추정가격</th>
              <th style={{ width: 110 }}>투찰마감일시</th>
              <th style={{ width: 110 }}>개찰일시</th>
              <th style={{ width: 80 }}>현설</th>
              <th style={{ width: 56 }}>분석</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={14} style={{ padding: 22, color: "#999" }}>
                  공고 데이터 로딩 중...
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={14} style={{ padding: 22, color: "#999" }}>
                  조건에 맞는 공고가 없습니다
                </td>
              </tr>
            )}
            {items.map((a, idx) => (
              <tr key={a.id} style={{ height: 40 }}>
                <td style={{ fontSize: 12 }}>{(page - 1) * pageSize + idx + 1}</td>
                <td style={{ textAlign: "left", maxWidth: 340, padding: "8px 8px" }}>
                  <Link
                    href={`/analysis/${a.id}`}
                    style={{
                      color: "var(--kbid-primary)",
                      fontWeight: 700,
                      fontSize: 13,
                      textDecoration: "none",
                    }}
                    className="hover:underline"
                  >
                    {a.title}
                  </Link>
                </td>
                <td style={{ fontFamily: "monospace", fontSize: 11, color: "#777" }}>
                  {a.bid_number}
                </td>
                <td>
                  <span
                    className="inline-block px-2 py-1 text-[11px] font-bold"
                    style={{
                      background:
                        a.type === "공사"
                          ? "#DCE8F6"
                          : a.type === "용역"
                          ? "#EEDCF6"
                          : "#E8E8E8",
                      color:
                        a.type === "공사"
                          ? "#0E47C8"
                          : a.type === "용역"
                          ? "#6F2B96"
                          : "#555",
                      borderRadius: 2,
                    }}
                  >
                    {a.type}
                  </span>
                </td>
                <td style={{ fontSize: 11, color: "#555" }}>
                  {a.license_category ?? "-"}
                </td>
                <td style={{ fontSize: 12, fontWeight: 600 }}>{a.area ?? "-"}</td>
                <td style={{ textAlign: "left", maxWidth: 140, fontSize: 12 }} className="truncate">
                  {a.org}
                </td>
                <td style={{ textAlign: "left", fontSize: 11, color: "#666" }} className="truncate">
                  {a.parent_org && a.parent_org !== a.org ? a.parent_org : "-"}
                </td>
                <td style={{ textAlign: "right", fontWeight: 700, fontSize: 13, color: "var(--kbid-text-strong)" }}>
                  {formatBudget(a.budget)}
                </td>
                <td style={{ textAlign: "right", color: "#666", fontSize: 12 }}>
                  {a.estimated_price ? formatBudget(a.estimated_price) : "-"}
                </td>
                <td style={{ fontSize: 11, color: "#555" }}>{a.deadline ?? "-"}</td>
                <td style={{ fontSize: 11, color: "#555" }}>{a.opening_at ?? "-"}</td>
                <td style={{ fontSize: 11, color: "#555" }}>{a.site_visit_at ?? "-"}</td>
                <td>
                  <Link
                    href={`/analysis/${a.id}`}
                    className="kbid-btn-primary"
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center",
                      padding: "5px 14px",
                      fontSize: 12,
                      fontWeight: 700,
                      borderRadius: 3,
                      minWidth: 56,
                      lineHeight: 1.2,
                      textDecoration: "none",
                    }}
                  >
                    분 석
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <KbidPager
        page={page}
        totalPages={totalPages}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(n) => {
          setPageSize(n);
          setPage(1);
        }}
      />
    </div>
  );
}
