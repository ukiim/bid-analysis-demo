"use client";

import { useState } from "react";
import type { FirstPlacePrediction } from "@/types/analysis";

interface Props {
  records: FirstPlacePrediction[];
  selectedRate?: number | null;
}

const PAGE_SIZE = 30;

export default function Tab4RateTable({ records, selectedRate }: Props) {
  const [page, setPage] = useState(1);
  const safeRecords = records ?? [];
  const totalPages = Math.max(1, Math.ceil(safeRecords.length / PAGE_SIZE));
  const slice = safeRecords.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  if (safeRecords.length === 0) {
    return (
      <div className="flex items-center justify-center h-[300px] text-gray-400 text-[13px]">
        사정률 데이터가 없습니다
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="text-[13px] font-bold text-[#3358A4]">사정률 표</div>
        {selectedRate != null && (
          <div className="text-[11px] bg-[#FFF7ED] border border-[#E8913A] text-[#E8913A] px-2.5 py-1 font-bold">
            ★ Tab3 선택 {selectedRate.toFixed(4)}% — 인접 항목 하이라이트
          </div>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[11px]">
          <thead>
            <tr className="bg-[#E8EDF3]">
              <th className="border border-gray-300 px-2 py-1.5 text-center font-semibold">No</th>
              <th className="border border-gray-300 px-2 py-1.5 text-left font-semibold">입찰일</th>
              <th className="border border-gray-300 px-2 py-1.5 text-left font-semibold">공고명</th>
              <th className="border border-gray-300 px-2 py-1.5 text-left font-semibold">발주처</th>
              <th className="border border-gray-300 px-2 py-1.5 text-center font-semibold">사정률</th>
              <th className="border border-gray-300 px-2 py-1.5 text-center font-semibold">낙찰률</th>
              <th className="border border-gray-300 px-2 py-1.5 text-right font-semibold">낙찰금액</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((r, i) => {
              const isMatch =
                selectedRate != null &&
                Math.abs(r.assessment_rate - selectedRate) < 0.1;
              return (
                <tr
                  key={i}
                  className={isMatch ? "bg-[#FFF7ED]" : "hover:bg-blue-50"}
                >
                  <td className="border border-gray-300 px-2 py-1 text-center text-gray-500">
                    {(page - 1) * PAGE_SIZE + i + 1}
                  </td>
                  <td className="border border-gray-300 px-2 py-1 text-gray-600">{r.date}</td>
                  <td className="border border-gray-300 px-2 py-1 max-w-[250px] truncate">{r.title}</td>
                  <td className="border border-gray-300 px-2 py-1 text-gray-600">{r.org}</td>
                  <td className="border border-gray-300 px-2 py-1 text-center font-semibold">
                    {r.assessment_rate.toFixed(4)}%
                  </td>
                  <td className="border border-gray-300 px-2 py-1 text-center text-[#3358A4] font-semibold">
                    {r.first_place_rate.toFixed(4)}%
                  </td>
                  <td className="border border-gray-300 px-2 py-1 text-right">
                    {r.first_place_amount?.toLocaleString() ?? "-"}원
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 py-2 mt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="px-2 py-1 text-[11px] border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            ◀
          </button>
          {Array.from({ length: Math.min(10, totalPages) }, (_, i) => {
            const start = Math.max(1, Math.min(page - 5, totalPages - 9));
            const p = start + i;
            if (p > totalPages) return null;
            return (
              <button
                key={p}
                onClick={() => setPage(p)}
                className={`px-2 py-1 text-[11px] border ${
                  p === page
                    ? "bg-[#3358A4] text-white border-[#3358A4]"
                    : "border-gray-300 hover:bg-gray-100"
                }`}
              >
                {p}
              </button>
            );
          })}
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="px-2 py-1 text-[11px] border border-gray-300 disabled:opacity-40 hover:bg-gray-100"
          >
            ▶
          </button>
        </div>
      )}
    </div>
  );
}
