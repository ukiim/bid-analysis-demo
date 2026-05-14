"use client";

/**
 * 10년 이전 데이터 자동/수동 삭제 — PDF 03 §10
 * (백엔드 신규: /api/v1/admin/purge?years=10 — 데모 단계에서 응답 fallback)
 */
import { useState } from "react";

export default function PurgeOldDataCard() {
  const [autoEnabled, setAutoEnabled] = useState(true);
  const [retentionYears, setRetentionYears] = useState(10);
  const [busy, setBusy] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const handleManualPurge = async () => {
    if (!confirm(`${retentionYears}년 이전 데이터를 영구 삭제합니다. 진행할까요?`)) {
      return;
    }
    setBusy(true);
    setLastResult(null);
    try {
      const token =
        typeof window !== "undefined" ? localStorage.getItem("token") : null;
      const res = await fetch(
        `/api/v1/admin/purge?years=${retentionYears}`,
        {
          method: "POST",
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        }
      );
      if (res.ok) {
        const d = await res.json();
        setLastResult(
          `✓ ${d.deleted_count?.toLocaleString() ?? "?"}건 삭제됨 (${d.message ?? "완료"})`
        );
      } else if (res.status === 404) {
        // 백엔드 미구현 — 데모용 fallback
        setLastResult(
          "ℹ 데모: 백엔드 /admin/purge 미구현 (PDF 03 §10 향후 구현)"
        );
      } else {
        setLastResult(`⚠ 실패 (HTTP ${res.status})`);
      }
    } catch (e) {
      setLastResult(`⚠ ${e instanceof Error ? e.message : "오류"}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border bg-white" style={{ borderColor: "var(--kbid-border)" }}>
      <div
        className="text-white px-3 py-2 text-[12px] font-bold"
        style={{ background: "linear-gradient(to bottom, #346081, #1E3A6B)" }}
      >
        오래된 데이터 정리 (PDF 03 §10 — 10년 자동/수동 삭제)
      </div>
      <div className="p-3 space-y-3 text-[12px]">
        <div className="flex items-center justify-between p-2 border" style={{ borderColor: "var(--kbid-border)", background: "var(--kbid-panel-bg)" }}>
          <div>
            <div className="font-bold" style={{ color: "var(--kbid-text-strong)" }}>
              자동 삭제
            </div>
            <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
              매월 1일 새벽 02:00 (cron — purge_old_data.py)
            </div>
          </div>
          <button
            onClick={() => setAutoEnabled((v) => !v)}
            className="kbid-btn-secondary"
            style={{
              padding: "4px 14px",
              background: autoEnabled ? "#DDF1DF" : "#FFE5E0",
              color: autoEnabled ? "#2B8B3C" : "#A8231D",
            }}
          >
            {autoEnabled ? "● 활성" : "○ 비활성"}
          </button>
        </div>

        <div className="flex items-center gap-2">
          <span style={{ color: "var(--kbid-text-meta)" }}>보관 기간</span>
          <select
            className="text-[12px] py-1 px-2 border"
            style={{ borderColor: "var(--kbid-border)" }}
            value={retentionYears}
            onChange={(e) => setRetentionYears(Number(e.target.value))}
          >
            <option value={5}>5년</option>
            <option value={7}>7년</option>
            <option value={10}>10년</option>
            <option value={15}>15년</option>
          </select>
          <span className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
            이전 데이터 삭제
          </span>
          <button
            onClick={handleManualPurge}
            disabled={busy}
            className="kbid-btn-primary ml-auto"
            style={{ padding: "4px 14px", fontSize: 12 }}
          >
            {busy ? "처리 중..." : "🗑 수동 삭제 실행"}
          </button>
        </div>

        {lastResult && (
          <div
            className="px-2.5 py-2 text-[11px] border"
            style={{
              background: lastResult.startsWith("✓")
                ? "#DDF1DF"
                : lastResult.startsWith("ℹ")
                ? "#E8EDF3"
                : "#FFE5E0",
              borderColor: lastResult.startsWith("✓")
                ? "#2B8B3C"
                : lastResult.startsWith("ℹ")
                ? "var(--kbid-border)"
                : "#D9342B",
              color: lastResult.startsWith("✓")
                ? "#2B8B3C"
                : lastResult.startsWith("ℹ")
                ? "var(--kbid-text-meta)"
                : "#A8231D",
            }}
          >
            {lastResult}
          </div>
        )}
      </div>
    </div>
  );
}
