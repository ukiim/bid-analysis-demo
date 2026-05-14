"use client";

import AmLineChart from "@/components/charts/AmLineChart";
import type { TrendPoint } from "@/types/analysis";

interface Props {
  series: TrendPoint[];
  selectedRate?: number | null;
}

// v4 — amCharts 5 시계열 라인 차트로 마이그레이션
export default function Tab1RateChart({ series, selectedRate }: Props) {
  if (series.length === 0) {
    return (
      <div className="flex items-center justify-center h-[350px] text-gray-400 text-[13px]">
        트렌드 데이터가 없습니다
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <div className="text-[13px] font-bold text-[#437194]">
          사정률 그래프 분석
        </div>
        {selectedRate != null && (
          <div className="text-[11px] bg-[#FFF7ED] border border-[#E8913A] text-[#E8913A] px-2.5 py-1 font-bold">
            ★ Tab3에서 선택된 사정률: {selectedRate.toFixed(4)}%
          </div>
        )}
      </div>
      <AmLineChart data={series} height={350} referenceRate={selectedRate} />
    </div>
  );
}
