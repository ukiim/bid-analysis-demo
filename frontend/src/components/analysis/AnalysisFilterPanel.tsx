"use client";

import type { AnnouncementMeta, AnalysisSearchFilters } from "@/types/analysis";

interface Props {
  announcement: AnnouncementMeta | null;
  filters: AnalysisSearchFilters;
  dataCount: number;
  onFiltersChange: (f: AnalysisSearchFilters) => void;
  onSearch: () => void;
}

const PERIOD_OPTIONS = [
  { label: "1개월", value: 1 },
  { label: "3개월", value: 3 },
  { label: "6개월", value: 6 },
  { label: "9개월", value: 9 },
  { label: "1년", value: 12 },
  { label: "2년", value: 24 },
];

const CATEGORY_OPTIONS = [
  { label: "전체", value: "all" },
  { label: "구매", value: "purchase" },
  { label: "공사", value: "construction" },
  { label: "용역", value: "service" },
  { label: "동일업종", value: "same_industry" },
];

const labelCls = "bg-[#E8EDF3] border border-gray-300 px-3 py-2 text-[12px] font-semibold text-gray-700 whitespace-nowrap";
const cellCls = "border border-gray-300 px-3 py-2";
const inputCls = "w-full text-[12px] py-1 px-2 border border-gray-300 outline-none focus:border-[#3358A4]";
const readonlyCls = "w-full text-[12px] py-1 px-2 bg-gray-50 text-gray-600";

export default function AnalysisFilterPanel({
  announcement,
  filters,
  dataCount,
  onFiltersChange,
  onSearch,
}: Props) {
  const set = (patch: Partial<AnalysisSearchFilters>) =>
    onFiltersChange({ ...filters, ...patch });

  return (
    <div className="bg-white border border-gray-300 mx-4 mt-3">
      <table className="w-full border-collapse text-[12px]">
        <tbody>
          {/* Row 1 */}
          <tr>
            <td className={labelCls}>공고명</td>
            <td className={cellCls}>
              <input className={readonlyCls} readOnly value={announcement?.title ?? ""} />
            </td>
            <td className={labelCls}>공고번호</td>
            <td className={cellCls}>
              <input className={readonlyCls} readOnly value={announcement?.id ?? ""} />
            </td>
          </tr>
          {/* Row 2 */}
          <tr>
            <td className={labelCls}>발주처</td>
            <td className={cellCls}>
              <div className="flex gap-1">
                <input
                  className={inputCls}
                  placeholder="발주처 검색"
                  value={filters.org_search}
                  onChange={(e) => set({ org_search: e.target.value })}
                />
                <button
                  onClick={onSearch}
                  className="px-3 py-1 bg-[#3358A4] text-white text-[11px] whitespace-nowrap hover:bg-[#2C4F8A]"
                >
                  발주처검색
                </button>
              </div>
            </td>
            <td className={labelCls}>구분</td>
            <td className={cellCls}>
              <span className="text-[12px] text-gray-600">
                {announcement?.type === "construction" ? "공사" : announcement?.type === "service" ? "용역" : announcement?.type ?? "-"}
              </span>
            </td>
          </tr>
          {/* Row 3 */}
          <tr>
            <td className={labelCls}>예가변동폭</td>
            <td className={cellCls}>
              <div className="flex items-center gap-1">
                <input
                  type="number"
                  className={`${inputCls} w-16`}
                  value={filters.price_volatility_min}
                  onChange={(e) => set({ price_volatility_min: Number(e.target.value) })}
                />
                <span className="text-[11px]">% ~</span>
                <input
                  type="number"
                  className={`${inputCls} w-16`}
                  value={filters.price_volatility_max}
                  onChange={(e) => set({ price_volatility_max: Number(e.target.value) })}
                />
                <span className="text-[11px]">%</span>
                <button
                  onClick={onSearch}
                  className="px-3 py-1 bg-[#3358A4] text-white text-[11px] whitespace-nowrap hover:bg-[#2C4F8A]"
                >
                  적용
                </button>
              </div>
            </td>
            <td className={labelCls}>투찰하한율</td>
            <td className={cellCls}>
              <input className={readonlyCls} readOnly value="87.745%" />
            </td>
          </tr>
          {/* Row 4 */}
          <tr>
            <td className={labelCls}>기초금액</td>
            <td className={cellCls}>
              <input
                className={readonlyCls}
                readOnly
                value={announcement?.budget ? `${announcement.budget.toLocaleString()}원` : "-"}
              />
            </td>
            <td className={labelCls}>추정가격</td>
            <td className={cellCls}>
              <input className={readonlyCls} readOnly value="-" />
            </td>
          </tr>
          {/* Row 5 */}
          <tr>
            <td className={labelCls}>업종조건</td>
            <td className={cellCls}>
              <div className="flex gap-1">
                {CATEGORY_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => set({ category_filter: opt.value })}
                    className={`px-2.5 py-1 text-[11px] border ${
                      filters.category_filter === opt.value
                        ? "bg-[#3358A4] text-white border-[#3358A4]"
                        : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </td>
            <td className={labelCls}>분석건수</td>
            <td className={cellCls}>
              <input className={readonlyCls} readOnly value={`${dataCount}건`} />
            </td>
          </tr>
          {/* Row 6 */}
          <tr>
            <td className={labelCls}>분석기간</td>
            <td className={cellCls} colSpan={3}>
              <div className="flex items-center gap-1">
                {PERIOD_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => set({ period_months: opt.value })}
                    className={`px-2.5 py-1 text-[11px] border ${
                      filters.period_months === opt.value
                        ? "bg-[#3358A4] text-white border-[#3358A4]"
                        : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
                <button
                  onClick={onSearch}
                  className="ml-2 px-4 py-1 bg-[#3358A4] text-white text-[11px] font-bold hover:bg-[#2C4F8A]"
                >
                  검색
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
