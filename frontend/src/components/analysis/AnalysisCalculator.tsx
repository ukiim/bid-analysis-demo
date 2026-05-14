"use client";

/**
 * KBID 투찰금액 계산기 — v5 (PDF 04 §3 조정값 List Box 추가)
 *
 * KBID 동일 4-열: 기초금액 / 투찰하한율 / 선택사정률 / 투찰금액
 * + v5: 결과값 조정 (List Box, -0.2~+0.2 5단)
 */
import { useState, useEffect } from "react";

interface Props {
  baseAmount: number | null;
  selectedRate: number | null;
}

const ADJUSTMENT_OPTIONS = [
  { value: -0.2, label: "-0.2%" },
  { value: -0.1, label: "-0.1%" },
  { value: 0, label: "조정 없음" },
  { value: 0.1, label: "+0.1%" },
  { value: 0.2, label: "+0.2%" },
];

export default function AnalysisCalculator({ baseAmount, selectedRate }: Props) {
  const [bidLowerRate, setBidLowerRate] = useState(87.745);
  const [manualRate, setManualRate] = useState<number | null>(null);
  const [adjustment, setAdjustment] = useState<number>(0);

  const baseRate = manualRate ?? selectedRate;
  const effectiveRate = baseRate != null ? +(baseRate + adjustment).toFixed(4) : null;
  const bidAmount =
    baseAmount && effectiveRate
      ? Math.round(baseAmount * (effectiveRate / 100))
      : null;

  useEffect(() => {
    if (selectedRate != null) setManualRate(null);
  }, [selectedRate]);

  return (
    <div className="mx-4 mt-3 mb-6 bg-white border border-gray-300">
      <div className="bg-gradient-to-b from-[#5481B8] to-[#437194] text-white px-4 py-2 text-[12px] font-bold">
        투찰금액 계산
      </div>
      <div className="p-4">
        <table className="border-collapse text-[12px]">
          <tbody>
            <tr>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                기초금액
              </td>
              <td className="border border-gray-300 px-3 py-2 min-w-[160px]">
                {baseAmount ? `${baseAmount.toLocaleString()}원` : "-"}
              </td>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                투찰하한율
              </td>
              <td className="border border-gray-300 px-3 py-2">
                <input
                  type="number"
                  step="0.001"
                  className="w-20 text-[12px] py-0.5 px-1 border border-gray-300 outline-none"
                  value={bidLowerRate}
                  onChange={(e) => setBidLowerRate(Number(e.target.value))}
                />
                <span className="ml-1">%</span>
              </td>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                선택사정률
              </td>
              <td className="border border-gray-300 px-3 py-2">
                <input
                  type="number"
                  step="0.001"
                  className="w-24 text-[12px] py-0.5 px-1 border border-gray-300 outline-none"
                  value={baseRate ?? ""}
                  onChange={(e) =>
                    setManualRate(e.target.value ? Number(e.target.value) : null)
                  }
                  placeholder="사정률 입력"
                />
                <span className="ml-1">%</span>
              </td>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                조정값
                <span className="text-[10px] block text-gray-500">(PDF 04 §3)</span>
              </td>
              <td className="border border-gray-300 px-3 py-2">
                <select
                  className="w-24 text-[12px] py-0.5 px-1 border border-gray-300 outline-none"
                  value={adjustment}
                  onChange={(e) => setAdjustment(Number(e.target.value))}
                >
                  {ADJUSTMENT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </td>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                투찰금액
              </td>
              <td className="border border-gray-300 px-3 py-2 font-bold text-[#437194] text-[14px]">
                {bidAmount ? `${bidAmount.toLocaleString()}원` : "-"}
                {effectiveRate != null && (
                  <div className="text-[10px] text-gray-500 font-normal mt-0.5">
                    적용 사정률 {effectiveRate.toFixed(4)}%
                    {adjustment !== 0 && (
                      <span> (조정 {adjustment > 0 ? "+" : ""}{adjustment}%)</span>
                    )}
                  </div>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
