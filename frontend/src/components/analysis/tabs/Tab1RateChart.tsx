"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { TrendPoint } from "@/types/analysis";

interface Props {
  series: TrendPoint[];
  selectedRate?: number | null;
}

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
        <div className="text-[13px] font-bold text-[#3358A4]">
          사정률 그래프 분석
        </div>
        {selectedRate != null && (
          <div className="text-[11px] bg-[#FFF7ED] border border-[#E8913A] text-[#E8913A] px-2.5 py-1 font-bold">
            ★ Tab3에서 선택된 사정률: {selectedRate.toFixed(4)}%
          </div>
        )}
      </div>
      <ResponsiveContainer width="100%" height={350}>
        <LineChart data={series} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11 }}
            tickLine={false}
          />
          <YAxis
            domain={["auto", "auto"]}
            tick={{ fontSize: 11 }}
            tickFormatter={(v: number) => `${v.toFixed(1)}%`}
          />
          <Tooltip
            formatter={(value: number) => [`${value.toFixed(4)}%`, "사정률"]}
            labelFormatter={(label: string) => `기간: ${label}`}
            contentStyle={{ fontSize: 12 }}
          />
          <ReferenceLine y={100} stroke="#E8913A" strokeDasharray="5 5" label={{ value: "100%", fontSize: 11, fill: "#E8913A" }} />
          {selectedRate != null && (
            <ReferenceLine
              y={selectedRate}
              stroke="#3358A4"
              strokeWidth={2}
              label={{
                value: `선택: ${selectedRate.toFixed(2)}%`,
                fontSize: 11,
                fill: "#3358A4",
                position: "left",
              }}
            />
          )}
          <Line
            type="monotone"
            dataKey="avg_rate"
            stroke="#3358A4"
            strokeWidth={2}
            dot={{ r: 3, fill: "#3358A4" }}
            name="평균 사정률"
          />
          <Line
            type="monotone"
            dataKey="min_rate"
            stroke="#4CAF50"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            name="최저 사정률"
          />
          <Line
            type="monotone"
            dataKey="max_rate"
            stroke="#E8913A"
            strokeWidth={1}
            strokeDasharray="3 3"
            dot={false}
            name="최고 사정률"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
