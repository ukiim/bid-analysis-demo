"use client";

/**
 * Tab5: 업체사정률 분석 (KBID 동등성 — 1차 데모 검토 §2)
 *
 * KBID 캡쳐 동일 형식:
 * - 세로축: 사정률 (확장 -3% ~ +3% 변동범위, 실제로는 97~103% 범위에서 0.01 단위)
 * - 가로축: 회사 8명 (페이지네이션 좌/우)
 * - 셀: 해당 회사가 해당 사정률로 투찰한 건수 (0 이면 회색, >0 이면 파란 강조)
 * - 좌측 사이드: 회사명 + 최근 사정률 + 순위 (체크박스로 표시/숨김)
 */
import { useMemo, useState } from "react";
import type { AnalysisCompanyRatesResponse, CompanyRateRecord } from "@/types/analysis";

interface Props {
  data: AnalysisCompanyRatesResponse | null;
  selectedRate: number | null;
  onRateSelect: (rate: number) => void;
}

const COMPANIES_PER_PAGE = 8;

// 사정률 범위 (97% ~ 103%) — 600행 (0.01% 단위)
const RATE_MIN = 97.0;
const RATE_MAX = 103.0;
const RATE_STEP = 0.01;

export default function Tab5CompanyRates({ data, selectedRate, onRateSelect }: Props) {
  const [companyPage, setCompanyPage] = useState(0);
  const [hiddenCompanies, setHiddenCompanies] = useState<Set<string>>(new Set());

  // 회사별 사정률 집계 (KBID 매트릭스용)
  // company_rates[] 는 (company, rate, ranking, is_first_place) — 한 회사가 여러 건 가능
  const { companies, companyMap } = useMemo(() => {
    const map = new Map<string, CompanyRateRecord[]>();
    if (data?.company_rates) {
      for (const r of data.company_rates) {
        const key = r.company || "(미상)";
        if (!map.has(key)) map.set(key, []);
        map.get(key)!.push(r);
      }
    }
    // 순위 좋은 회사 우선 (1순위 가진 회사 → 평균 ranking ASC)
    const list = Array.from(map.entries())
      .map(([name, records]) => {
        const has1st = records.some((r) => r.is_first_place);
        const avgRank =
          records.reduce((s, r) => s + (r.ranking ?? 99), 0) / records.length;
        const latestRate = records[0]?.rate ?? 0;
        return { name, records, has1st, avgRank, latestRate };
      })
      .sort((a, b) =>
        a.has1st !== b.has1st ? (a.has1st ? -1 : 1) : a.avgRank - b.avgRank
      );
    return { companies: list, companyMap: map };
  }, [data]);

  const totalPages = Math.max(1, Math.ceil(companies.length / COMPANIES_PER_PAGE));
  const visibleCompanies = companies
    .filter((c) => !hiddenCompanies.has(c.name))
    .slice(companyPage * COMPANIES_PER_PAGE, (companyPage + 1) * COMPANIES_PER_PAGE);

  // 매트릭스 행 (사정률 -> 회사별 cell)
  const matrixRows = useMemo(() => {
    const rows: { rate: number; cells: { count: number }[] }[] = [];
    // 데이터 범위 동적 추정 — 실 데이터 min/max 기준 ±0.5%
    let minR = RATE_MIN;
    let maxR = RATE_MAX;
    if (data?.company_rates && data.company_rates.length > 0) {
      const rates = data.company_rates.map((r) => r.rate);
      minR = Math.floor((Math.min(...rates) - 0.5) * 100) / 100;
      maxR = Math.ceil((Math.max(...rates) + 0.5) * 100) / 100;
    }
    const steps = Math.min(800, Math.ceil((maxR - minR) / RATE_STEP));
    for (let i = 0; i <= steps; i++) {
      const rate = Math.round((minR + i * RATE_STEP) * 100) / 100;
      const cells = visibleCompanies.map((c) => {
        const count = c.records.filter(
          (r) => Math.abs(r.rate - rate) < RATE_STEP / 2
        ).length;
        return { count };
      });
      rows.push({ rate, cells });
    }
    return rows;
  }, [data, visibleCompanies]);

  if (!data || !data.company_rates || data.company_rates.length === 0) {
    return (
      <div className="flex items-center justify-center h-[400px] text-gray-400 text-[13px]">
        업체사정률 데이터가 없습니다 (해당 공고에 투찰한 업체 정보 없음)
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="text-[13px] font-bold text-[#3358A4]">업체사정률 분석</div>
          <div className="text-[11px] text-gray-500 mt-0.5">
            전체 업체 {data.total_companies.toLocaleString()}곳 · 고유 사정률{" "}
            {data.unique_rate_count}건 · 표시 중 {companies.length}곳
            {data.refined_rate != null && (
              <span className="ml-2 text-[#3358A4] font-bold">
                · 세밀 사정률 {data.refined_rate.toFixed(4)}%
              </span>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2 text-[11px]">
          <button
            disabled={companyPage <= 0}
            onClick={() => setCompanyPage((p) => Math.max(0, p - 1))}
            className="px-3 py-1.5 border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            ◀ 이전 8곳
          </button>
          <span className="px-2 text-gray-600">
            {companyPage + 1} / {totalPages}
          </span>
          <button
            disabled={companyPage >= totalPages - 1}
            onClick={() => setCompanyPage((p) => Math.min(totalPages - 1, p + 1))}
            className="px-3 py-1.5 border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            다음 8곳 ▶
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* 좌측 사이드: 회사 목록 + 체크박스 */}
        <div className="col-span-3 border border-gray-300 max-h-[600px] overflow-y-auto">
          <div className="bg-gradient-to-b from-[#4A7ABF] to-[#3358A4] text-white px-3 py-1.5 text-[11px] font-bold sticky top-0">
            업체 목록 ({companies.length}곳)
          </div>
          <table className="w-full border-collapse text-[11px]">
            <thead>
              <tr className="bg-[#E8EDF3]">
                <th className="border border-gray-300 px-1.5 py-1 text-center">표시</th>
                <th className="border border-gray-300 px-1.5 py-1 text-left">업체명</th>
                <th className="border border-gray-300 px-1.5 py-1 text-center">사정률</th>
                <th className="border border-gray-300 px-1.5 py-1 text-center">순위</th>
              </tr>
            </thead>
            <tbody>
              {companies.slice(0, 50).map((c) => (
                <tr key={c.name} className="hover:bg-blue-50">
                  <td className="border border-gray-300 px-1.5 py-1 text-center">
                    <input
                      type="checkbox"
                      checked={!hiddenCompanies.has(c.name)}
                      onChange={(e) => {
                        const next = new Set(hiddenCompanies);
                        if (e.target.checked) next.delete(c.name);
                        else next.add(c.name);
                        setHiddenCompanies(next);
                      }}
                    />
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 max-w-[140px] truncate">
                    {c.has1st && <span className="text-[#E8913A] mr-0.5">★</span>}
                    {c.name}
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 text-center font-semibold">
                    {c.latestRate.toFixed(2)}%
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 text-center">
                    <span
                      className={`inline-flex items-center justify-center min-w-[20px] h-[16px] rounded-full text-[10px] font-bold ${
                        c.avgRank === 1
                          ? "bg-[#E8913A] text-white"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {Math.round(c.avgRank)}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* 우측: 큰 매트릭스 */}
        <div className="col-span-9 border border-gray-300 max-h-[600px] overflow-auto">
          <table className="border-collapse text-[10px]">
            <thead>
              <tr className="bg-[#E8EDF3] sticky top-0 z-10">
                <th className="border border-gray-300 px-1.5 py-1 text-center font-semibold sticky left-0 z-20 bg-[#E8EDF3] min-w-[60px]">
                  사정률 %
                </th>
                {visibleCompanies.map((c) => (
                  <th
                    key={c.name}
                    className="border border-gray-300 px-1 py-1 text-center font-semibold min-w-[80px]"
                    title={c.name}
                  >
                    <div className="truncate max-w-[80px]">{c.name}</div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {matrixRows.map((row) => {
                const isSelectedRow =
                  selectedRate != null &&
                  Math.abs(row.rate - selectedRate) < RATE_STEP / 2;
                const hasAny = row.cells.some((c) => c.count > 0);
                return (
                  <tr
                    key={row.rate}
                    className={isSelectedRow ? "bg-[#FFF7ED]" : ""}
                  >
                    <td
                      onClick={() => hasAny && onRateSelect(row.rate)}
                      className={`border border-gray-300 px-1.5 py-0.5 text-center font-mono sticky left-0 z-10 ${
                        isSelectedRow
                          ? "bg-[#3358A4] text-white font-bold cursor-pointer"
                          : hasAny
                          ? "bg-white cursor-pointer hover:bg-[#FFF7ED]"
                          : "bg-gray-50 text-gray-300"
                      }`}
                    >
                      {row.rate.toFixed(2)}
                    </td>
                    {row.cells.map((cell, idx) => (
                      <td
                        key={idx}
                        className={`border border-gray-300 px-1 py-0.5 text-center ${
                          cell.count > 0
                            ? "bg-[#3358A4] text-white font-bold"
                            : "text-gray-200"
                        }`}
                      >
                        {cell.count > 0 ? cell.count : ""}
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* 갭 분석 요약 (KBID 동등성: 사이드 정보) */}
      {data.gaps && data.gaps.length > 0 && (
        <div className="mt-3 border border-gray-300">
          <div className="bg-gradient-to-b from-[#4A7ABF] to-[#3358A4] text-white px-3 py-1.5 text-[11px] font-bold">
            업체 사정률 갭 분석 (상위 5건)
          </div>
          <table className="w-full border-collapse text-[11px]">
            <thead>
              <tr className="bg-[#E8EDF3]">
                <th className="border border-gray-300 px-2 py-1 text-center">No</th>
                <th className="border border-gray-300 px-2 py-1 text-center">시작</th>
                <th className="border border-gray-300 px-2 py-1 text-center">끝</th>
                <th className="border border-gray-300 px-2 py-1 text-center">갭 크기</th>
                <th className="border border-gray-300 px-2 py-1 text-center">중간값</th>
                <th className="border border-gray-300 px-2 py-1 text-center">선택</th>
              </tr>
            </thead>
            <tbody>
              {data.gaps.slice(0, 5).map((g, i) => (
                <tr key={i} className="hover:bg-blue-50">
                  <td className="border border-gray-300 px-2 py-1 text-center text-gray-500">{i + 1}</td>
                  <td className="border border-gray-300 px-2 py-1 text-center">{g.start.toFixed(4)}%</td>
                  <td className="border border-gray-300 px-2 py-1 text-center">{g.end.toFixed(4)}%</td>
                  <td className="border border-gray-300 px-2 py-1 text-center font-semibold text-[#E8913A]">
                    {g.size.toFixed(4)}
                  </td>
                  <td className="border border-gray-300 px-2 py-1 text-center font-bold text-[#3358A4]">
                    {g.midpoint.toFixed(4)}%
                  </td>
                  <td className="border border-gray-300 px-2 py-1 text-center">
                    <button
                      onClick={() => onRateSelect(g.midpoint)}
                      className="px-2 py-0.5 text-[10px] bg-[#3358A4] text-white hover:bg-[#2C4F8A]"
                    >
                      선택
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
