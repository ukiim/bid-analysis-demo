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
  const [preview, setPreview] = useState<{ ann: number; res: number; cutoff: string } | null>(null);

  const authHdrs = (): HeadersInit => {
    const token =
      typeof window !== "undefined" ? localStorage.getItem("token") : null;
    return token ? { Authorization: `Bearer ${token}` } : {};
  };

  const handlePreview = async () => {
    setBusy(true);
    setLastResult(null);
    try {
      const res = await fetch(
        `/api/v1/admin/purge?years=${retentionYears}&dry_run=true`,
        { method: "POST", headers: authHdrs() }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setPreview({
        ann: d.announcements_to_delete ?? 0,
        res: d.results_to_delete ?? 0,
        cutoff: d.cutoff,
      });
    } catch (e) {
      setLastResult(`⚠ 미리보기 실패: ${e instanceof Error ? e.message : "오류"}`);
    } finally {
      setBusy(false);
    }
  };

  const handleManualPurge = async () => {
    if (!preview) {
      alert("먼저 '미리보기'로 삭제 대상 건수를 확인하세요.");
      return;
    }
    if (preview.ann === 0 && preview.res === 0) {
      alert("삭제할 데이터가 없습니다.");
      return;
    }
    if (!confirm(
      `${retentionYears}년 이전 데이터를 영구 삭제합니다.\n\n` +
      `공고 ${preview.ann.toLocaleString()}건 + 낙찰결과 ${preview.res.toLocaleString()}건\n` +
      `cutoff: ${preview.cutoff}\n\n` +
      `진행할까요? 이 작업은 되돌릴 수 없습니다.`
    )) {
      return;
    }
    setBusy(true);
    setLastResult(null);
    try {
      const res = await fetch(
        `/api/v1/admin/purge?years=${retentionYears}`,
        { method: "POST", headers: authHdrs() }
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setLastResult(
        `✓ 공고 ${d.announcements_deleted?.toLocaleString() ?? 0}건 + ` +
        `낙찰결과 ${d.results_deleted?.toLocaleString() ?? 0}건 삭제 완료 (cutoff ${d.cutoff})`
      );
      setPreview(null);
    } catch (e) {
      setLastResult(`⚠ 삭제 실패: ${e instanceof Error ? e.message : "오류"}`);
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

        <div className="flex items-center gap-2 flex-wrap">
          <span style={{ color: "var(--kbid-text-meta)" }}>보관 기간</span>
          <select
            className="text-[12px] py-1 px-2 border"
            style={{ borderColor: "var(--kbid-border)" }}
            value={retentionYears}
            onChange={(e) => {
              setRetentionYears(Number(e.target.value));
              setPreview(null);
            }}
          >
            <option value={1}>1년 (테스트)</option>
            <option value={3}>3년</option>
            <option value={5}>5년</option>
            <option value={7}>7년</option>
            <option value={10}>10년 (기본)</option>
            <option value={15}>15년</option>
          </select>
          <span className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
            이전 데이터 삭제
          </span>
          <div className="flex-1" />
          <button
            onClick={handlePreview}
            disabled={busy}
            className="kbid-btn-secondary"
            style={{ padding: "4px 12px", fontSize: 12 }}
          >
            {busy && !preview ? "조회 중..." : "🔍 미리보기"}
          </button>
          <button
            onClick={handleManualPurge}
            disabled={busy || !preview}
            className="kbid-btn-primary"
            style={{ padding: "4px 14px", fontSize: 12 }}
            title={!preview ? "먼저 미리보기로 확인" : "영구 삭제"}
          >
            {busy && preview ? "삭제 중..." : "🗑 수동 삭제 실행"}
          </button>
        </div>

        {preview && (
          <div
            className="px-2.5 py-2 text-[11px] border"
            style={{
              background: "#FFF7ED",
              borderColor: "#E8913A",
              color: "#C56F1A",
            }}
          >
            🔍 삭제 대상 (cutoff {preview.cutoff}):{" "}
            <strong>공고 {preview.ann.toLocaleString()}건 + 낙찰결과 {preview.res.toLocaleString()}건</strong>
          </div>
        )}

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
