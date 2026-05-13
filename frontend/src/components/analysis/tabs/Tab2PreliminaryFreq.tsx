"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { PreliminaryFreqBin } from "@/types/analysis";

interface Props {
  bins: PreliminaryFreqBin[];
  total: number;
}

export default function Tab2PreliminaryFreq({ bins, total }: Props) {
  if (bins.length === 0) {
    return (
      <div className="flex items-center justify-center h-[350px] text-gray-400 text-[13px]">
        예가 추첨 빈도 데이터가 없습니다
      </div>
    );
  }

  const maxCount = Math.max(...bins.map((b) => b.count));

  return (
    <div>
      <div className="text-[13px] font-bold text-[#3358A4] mb-1">
        추첨된 예가빈도수 분석
      </div>
      <div className="text-[11px] text-gray-500 mb-3">
        총 {total}건의 예정가격 추첨 빈도 분포
      </div>
      <ResponsiveContainer width="100%" height={350}>
        <BarChart data={bins} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" vertical={false} />
          <XAxis
            dataKey="number"
            tick={{ fontSize: 11 }}
            label={{ value: "예가번호", position: "insideBottom", offset: -2, fontSize: 11 }}
          />
          <YAxis
            tick={{ fontSize: 11 }}
            label={{ value: "빈도", angle: -90, position: "insideLeft", fontSize: 11 }}
          />
          <Tooltip
            formatter={(value: number) => [`${value}회`, "빈도"]}
            contentStyle={{ fontSize: 12 }}
          />
          <Bar dataKey="count" radius={[2, 2, 0, 0]}>
            {bins.map((entry, index) => (
              <Cell
                key={index}
                fill={entry.count === maxCount ? "#E8913A" : "#3358A4"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
