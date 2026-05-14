"use client";

import AmHistogram from "@/components/charts/AmHistogram";
import type { PreliminaryFreqBin } from "@/types/analysis";

interface Props {
  bins: PreliminaryFreqBin[];
  total: number;
}

// v4 — Recharts → amCharts 마이그레이션 (KBID 동등 검정 막대)
export default function Tab2PreliminaryFreq({ bins, total }: Props) {
  if (bins.length === 0) {
    return (
      <div className="flex items-center justify-center h-[350px] text-gray-400 text-[13px]">
        예가 추첨 빈도 데이터가 없습니다
      </div>
    );
  }

  const maxCount = Math.max(...bins.map((b) => b.count));
  // AmHistogram의 데이터 포맷 (rate / count / first_place) 에 맞춰 변환
  // 여기서는 rate=number(예가번호), count=count, first_place=peak 강조
  const chartData = bins.map((b) => ({
    rate: b.number,
    count: b.count,
    first_place: b.count === maxCount ? b.count : 0,
  }));

  return (
    <div>
      <div className="text-[13px] font-bold text-[#437194] mb-1">
        추첨된 예가빈도수 분석
      </div>
      <div className="text-[11px] text-gray-500 mb-3">
        총 {total}건의 예정가격 추첨 빈도 분포 (피크 = 오렌지)
      </div>
      <AmHistogram data={chartData} height={350} />
    </div>
  );
}
