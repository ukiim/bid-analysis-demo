"use client";

/**
 * 투찰리스트 패널 — PDF 03 §9
 * 분석 페이지에서 "투찰리스트 담기" → localStorage 누적
 * 엑셀 다운로드 (백엔드 /api/v1/analysis/export/bid_list 또는 클라이언트 CSV)
 */
import { useEffect, useState } from "react";
import {
  loadBidList,
  removeFromBidList,
  type BidListItem,
} from "@/lib/bidList";

interface Props {
  onClose: () => void;
}

export default function BidListPanel({ onClose }: Props) {
  const [items, setItems] = useState<BidListItem[]>([]);

  useEffect(() => {
    setItems(loadBidList());
  }, []);

  const handleRemove = (id: string) => {
    const next = removeFromBidList(id);
    setItems(next);
  };

  const handleClear = () => {
    if (!confirm("투찰리스트 전체를 비우시겠습니까?")) return;
    if (typeof window !== "undefined") localStorage.removeItem("bid_list");
    setItems([]);
  };

  const handleExportCSV = () => {
    if (items.length === 0) return;
    const header = "공고ID,공고명,발주처,기초금액,예측사정률,조정값,예상투찰금액,담은시각";
    const rows = items
      .map(
        (i) =>
          `${i.announcement_id},"${i.title.replace(/"/g, '""')}","${i.org}",${i.base_amount ?? ""},${i.predicted_rate},${i.adjustment},${i.predicted_bid_amount ?? ""},${i.added_at}`
      )
      .join("\n");
    const csv = "﻿" + header + "\n" + rows;
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `bid_list_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: "rgba(0,0,0,0.5)" }}
      onClick={onClose}
    >
      <div
        className="bg-white shadow-xl"
        style={{ width: 720, maxHeight: "80vh", overflow: "auto" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          className="text-white px-4 py-3 text-[13px] font-bold flex items-center justify-between"
          style={{ background: "var(--kbid-header-bg)" }}
        >
          <span>📋 투찰리스트 (PDF 03 §9 — {items.length}건)</span>
          <button
            onClick={onClose}
            className="text-white text-[14px] px-2 hover:bg-white/20"
          >
            ✕
          </button>
        </div>

        <div className="p-4">
          {items.length === 0 ? (
            <div className="py-10 text-center text-gray-500 text-[13px]">
              아직 담은 공고가 없습니다. 분석 페이지에서 "투찰리스트 담기" 버튼으로 추가하세요.
            </div>
          ) : (
            <>
              <table className="kbid-list-table mb-3">
                <thead>
                  <tr>
                    <th style={{ width: 40 }}>No</th>
                    <th>공고명 / 발주처</th>
                    <th style={{ width: 120 }}>기초금액</th>
                    <th style={{ width: 90 }}>예측 사정률</th>
                    <th style={{ width: 130 }}>예상 투찰금액</th>
                    <th style={{ width: 60 }}>삭제</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((it, i) => (
                    <tr key={it.announcement_id}>
                      <td>{i + 1}</td>
                      <td style={{ textAlign: "left", padding: "8px 10px" }}>
                        <div className="font-bold truncate" style={{ color: "var(--kbid-text-strong)" }}>
                          {it.title}
                        </div>
                        <div className="text-[10px] text-gray-500 mt-0.5">{it.org}</div>
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 600 }}>
                        {it.base_amount?.toLocaleString() ?? "-"}원
                      </td>
                      <td>
                        <span style={{ color: "var(--kbid-primary)", fontWeight: 700 }}>
                          {it.predicted_rate.toFixed(4)}%
                        </span>
                        {it.adjustment !== 0 && (
                          <div className="text-[10px] text-gray-500">
                            {it.adjustment > 0 ? "+" : ""}
                            {it.adjustment}% 조정
                          </div>
                        )}
                      </td>
                      <td style={{ textAlign: "right", fontWeight: 700, color: "#E8913A" }}>
                        {it.predicted_bid_amount?.toLocaleString() ?? "-"}원
                      </td>
                      <td>
                        <button
                          onClick={() => handleRemove(it.announcement_id)}
                          className="text-[10px] text-red-600 hover:underline"
                        >
                          삭제
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <div className="flex items-center gap-2 mt-3">
                <button
                  onClick={handleClear}
                  className="kbid-btn-secondary"
                  style={{ color: "#D9342B" }}
                >
                  🗑 전체 비우기
                </button>
                <div className="flex-1" />
                <button onClick={handleExportCSV} className="kbid-btn-primary">
                  📥 CSV 다운로드 ({items.length}건)
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
