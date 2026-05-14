"use client";

/**
 * NAS 다운로드 현황 — PDF 04 §1 (이어받기 + 진행률 표시)
 * 백엔드 /api/v1/admin/sync/status 연동.
 */
import { useEffect, useState, useCallback } from "react";

interface SyncJob {
  id: string;
  job_name: string;
  status: "in_progress" | "completed" | "failed";
  progress_pct: number;
  records_fetched: number;
  inserted_count: number;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  last_checkpoint: string | null;
  can_resume: boolean;
}

const STATUS_COLOR: Record<string, string> = {
  in_progress: "#2B8B3C",
  completed: "#346081",
  failed: "#D9342B",
};

const STATUS_LABEL: Record<string, string> = {
  in_progress: "다운로드 중",
  completed: "완료",
  failed: "실패",
};

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function NasStatusCard() {
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [runningCount, setRunningCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/v1/admin/sync/status", { headers: authHeaders() });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const d = await res.json();
      setJobs(d.jobs ?? []);
      setRunningCount(d.running_count ?? 0);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "조회 실패");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const t = setInterval(fetchStatus, 5000); // 5초마다 폴링
    return () => clearInterval(t);
  }, [fetchStatus]);

  const handleResume = async (jobId: string) => {
    setBusy(jobId);
    try {
      const res = await fetch(`/api/v1/admin/sync/${jobId}/retry`, {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchStatus();
    } catch (e) {
      alert(`재시도 실패: ${e instanceof Error ? e.message : "오류"}`);
    } finally {
      setBusy(null);
    }
  };

  const handleTriggerSync = async () => {
    setBusy("trigger");
    try {
      const res = await fetch("/api/v1/admin/sync", {
        method: "POST",
        headers: authHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await fetchStatus();
    } catch (e) {
      alert(`수집 트리거 실패: ${e instanceof Error ? e.message : "오류"}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="border bg-white" style={{ borderColor: "var(--kbid-border)" }}>
      <div
        className="text-white px-3 py-2 text-[12px] font-bold flex items-center justify-between"
        style={{ background: "var(--text)" }}
      >
        <span>NAS 다운로드 현황 (PDF 04 §1)</span>
        <span className="text-[10px] opacity-90">
          {runningCount}건 진행 / {jobs.length}건 표시
        </span>
      </div>
      <div className="p-3 space-y-3">
        {loading && <div className="text-[11px] text-gray-500">조회 중...</div>}
        {error && (
          <div className="text-[11px] px-2 py-1" style={{ background: "#FFE5E0", color: "#A8231D" }}>
            ! {error}
          </div>
        )}
        {!loading && jobs.length === 0 && (
          <div className="text-center py-6 text-[12px] text-gray-500">
            진행 중이거나 최근 완료된 수집 작업이 없습니다
            <div className="mt-3">
              <button
                onClick={handleTriggerSync}
                disabled={busy === "trigger"}
                className="kbid-btn-primary"
                style={{ padding: "5px 14px", fontSize: 12 }}
              >
                {busy === "trigger" ? "트리거 중..." : "지금 수집 시작"}
              </button>
            </div>
          </div>
        )}
        {jobs.map((j) => (
          <div key={j.id}>
            <div className="flex items-center justify-between mb-1">
              <div className="text-[12px] font-bold" style={{ color: "var(--kbid-text-strong)" }}>
                {j.job_name}
              </div>
              <div className="flex items-center gap-2 text-[11px]">
                <span
                  className="px-2 py-0.5 text-white text-[10px] font-bold"
                  style={{
                    background: STATUS_COLOR[j.status] ?? "#777",
                    borderRadius: 2,
                  }}
                >
                  {STATUS_LABEL[j.status] ?? j.status}
                </span>
                {j.can_resume && (
                  <button
                    onClick={() => handleResume(j.id)}
                    disabled={busy === j.id}
                    className="kbid-btn-secondary"
                    style={{ padding: "2px 8px", fontSize: 11 }}
                  >
                    {busy === j.id ? "재개 중..." : "이어받기"}
                  </button>
                )}
              </div>
            </div>
            <div
              className="relative h-5 overflow-hidden"
              style={{ background: "#E8EDF3", border: "1px solid var(--kbid-border)" }}
            >
              <div
                className="h-full"
                style={{
                  width: `${j.progress_pct.toFixed(2)}%`,
                  background:
                    j.status === "in_progress"
                      ? "var(--accent)"
                      : j.status === "failed"
                      ? "#D9342B"
                      : "#A0A8B3",
                  transition: "width 0.5s",
                }}
              />
              <div
                className="absolute inset-0 flex items-center justify-center font-bold text-white"
                style={{ fontSize: 10, textShadow: "0 1px 0 rgba(0,0,0,0.3)" }}
              >
                {j.progress_pct.toFixed(2)}% · 수집 {j.records_fetched.toLocaleString()} / 적재 {j.inserted_count.toLocaleString()}
              </div>
            </div>
            <div className="flex items-center gap-3 mt-1 text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
              {j.started_at && <span>시작 {j.started_at}</span>}
              {j.finished_at && <span>종료 {j.finished_at}</span>}
              {j.last_checkpoint && <span>체크포인트 {j.last_checkpoint}</span>}
              {j.error_message && (
                <span style={{ color: "#D9342B" }} className="truncate">
                  ! {j.error_message}
                </span>
              )}
            </div>
          </div>
        ))}
        {jobs.length > 0 && (
          <div className="pt-2 border-t flex justify-end" style={{ borderColor: "var(--kbid-border)" }}>
            <button
              onClick={handleTriggerSync}
              disabled={busy === "trigger"}
              className="kbid-btn-secondary"
              style={{ padding: "4px 12px", fontSize: 11 }}
            >
              {busy === "trigger" ? "트리거 중..." : "신규 수집 트리거"}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
