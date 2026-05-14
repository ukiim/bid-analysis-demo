"use client";

import { useState } from "react";
import type { ComprehensiveComparison } from "@/types/analysis";

interface Props {
  comparisons: ComprehensiveComparison[];
}

const PAGE_SIZE = 20;

export default function AnalysisDataTable({ comparisons }: Props) {
  const [page, setPage] = useState(1);
  const totalPages = Math.max(1, Math.ceil(comparisons.length / PAGE_SIZE));
  const slice = comparisons.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="mx-4 mt-2 bg-white border border-gray-300">
      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-[12px]">
          <thead>
            <tr className="bg-[#E8EDF3]">
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">No</th>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">입찰일시</th>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">공고명</th>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">발주처</th>
              <th className="border border-gray-300 px-3 py-2 text-center font-semibold">사정률</th>
              <th className="border border-gray-300 px-3 py-2 text-center font-semibold">낙찰률</th>
              <th className="border border-gray-300 px-3 py-2 text-center font-semibold">낙찰순위</th>
              <th className="border border-gray-300 px-3 py-2 text-center font-semibold">일치</th>
            </tr>
          </thead>
          <tbody>
            {slice.length === 0 && (
              <tr>
                <td colSpan={8} className="border border-gray-300 px-3 py-8 text-center text-gray-400">
                  데이터가 없습니다
                </td>
              </tr>
            )}
            {slice.map((row, i) => (
              <tr key={i} className="hover:bg-blue-50">
                <td className="border border-gray-300 px-3 py-1.5 text-gray-500">
                  {(page - 1) * PAGE_SIZE + i + 1}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-gray-600">
                  {row.date}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-[#437194] cursor-pointer hover:underline max-w-[300px] truncate">
                  {row.title}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-gray-600">
                  {row.org}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-center font-semibold">
                  {row.assessment_rate.toFixed(4)}%
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-center text-[#437194] font-semibold">
                  {row.first_place_rate != null ? `${row.first_place_rate.toFixed(4)}%` : "-"}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-center">
                  {/* 낙찰순위 (KBID 동등성 §1) */}
                  {row.rank != null ? (
                    <span
                      className={`inline-flex items-center justify-center min-w-[24px] h-[20px] rounded-full text-[11px] font-bold ${
                        row.rank === 1
                          ? "bg-[#E8913A] text-white"
                          : row.rank === 2
                          ? "bg-[#437194] text-white"
                          : row.rank === 3
                          ? "bg-[#8AA7C9] text-white"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {row.rank}
                    </span>
                  ) : (
                    <span className="text-gray-300">-</span>
                  )}
                </td>
                <td className="border border-gray-300 px-3 py-1.5 text-center">
                  {row.is_match ? (
                    <span className="text-[#4CAF50] font-bold">●</span>
                  ) : (
                    <span className="text-gray-300">○</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-1 py-2 border-t border-gray-300">
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
                    ? "bg-[#437194] text-white border-[#437194]"
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
