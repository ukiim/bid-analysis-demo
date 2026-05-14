"use client";

import { useState, useEffect } from "react";

interface Props {
  baseAmount: number | null;
  selectedRate: number | null;
}

export default function AnalysisCalculator({ baseAmount, selectedRate }: Props) {
  const [bidLowerRate, setBidLowerRate] = useState(87.745);
  const [manualRate, setManualRate] = useState<number | null>(null);

  const effectiveRate = manualRate ?? selectedRate;
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
                  value={effectiveRate ?? ""}
                  onChange={(e) =>
                    setManualRate(e.target.value ? Number(e.target.value) : null)
                  }
                  placeholder="사정률 입력"
                />
                <span className="ml-1">%</span>
              </td>
              <td className="bg-[#E8EDF3] border border-gray-300 px-3 py-2 font-semibold whitespace-nowrap">
                투찰금액
              </td>
              <td className="border border-gray-300 px-3 py-2 font-bold text-[#437194] text-[14px]">
                {bidAmount ? `${bidAmount.toLocaleString()}원` : "-"}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
