"use client";

import type { FrequencyStats } from "@/types/analysis";

interface Props {
  stats: FrequencyStats | null;
  dataCount: number;
  onExport: () => void;
}

export default function AnalysisSummaryBar({ stats, dataCount, onExport }: Props) {
  return (
    <div className="mx-4 mt-2 flex items-center justify-between bg-white border border-gray-300 px-4 py-2.5">
      <div className="flex items-center gap-6 text-[12px]">
        <span className="font-semibold text-gray-700">
          선택한 공고의 평균 사정률:{" "}
          <span className="text-[#3358A4] font-bold text-[14px]">
            {stats ? `${stats.mean.toFixed(4)}%` : "-"}
          </span>
          <span className="text-gray-400 ml-2">({dataCount}건)</span>
        </span>
        <div className="flex items-center gap-4">
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm bg-[#4CAF50]" />
            <span className="text-[11px] text-gray-600">최하 {stats ? `${stats.min.toFixed(4)}%` : "-"}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm bg-[#E8913A]" />
            <span className="text-[11px] text-gray-600">최고 {stats ? `${stats.max.toFixed(4)}%` : "-"}</span>
          </span>
          <span className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm bg-[#2C4F8A]" />
            <span className="text-[11px] text-gray-600">중간 {stats ? `${stats.median.toFixed(4)}%` : "-"}</span>
          </span>
        </div>
      </div>
      <button
        onClick={onExport}
        className="px-3 py-1.5 bg-[#3358A4] text-white text-[11px] font-bold hover:bg-[#2C4F8A]"
      >
        선택엑셀출력
      </button>
    </div>
  );
}
