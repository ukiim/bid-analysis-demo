"use client";

/**
 * NAS 다운로드 현황 — PDF 04 §1 (이어받기 + 진행률 표시)
 * 백엔드 신규 엔드포인트 미존재 시 데모 데이터 사용.
 */
import { useEffect, useState } from "react";

interface NasStatus {
  job_name: string;
  status: "running" | "paused" | "completed" | "error";
  total: number;
  done: number;
  remaining: number;
  speed_mb_per_sec: number;
  eta_seconds: number | null;
  last_resume_at: string | null;
}

const DEMO_STATUS: NasStatus[] = [
  {
    job_name: "G2B 공고 백필 (2019~2023)",
    status: "running",
    total: 1_388_494,
    done: 824_127,
    remaining: 564_367,
    speed_mb_per_sec: 2.4,
    eta_seconds: 1820,
    last_resume_at: "오늘 06:00",
  },
  {
    job_name: "낙찰 결과 백필 (2024~2026)",
    status: "paused",
    total: 92_140,
    done: 41_207,
    remaining: 50_933,
    speed_mb_per_sec: 0,
    eta_seconds: null,
    last_resume_at: "어제 22:31",
  },
];

const STATUS_COLOR: Record<NasStatus["status"], string> = {
  running: "#2B8B3C",
  paused: "#E8913A",
  completed: "#346081",
  error: "#D9342B",
};

const STATUS_LABEL: Record<NasStatus["status"], string> = {
  running: "다운로드 중",
  paused: "일시정지",
  completed: "완료",
  error: "오류",
};

export default function NasStatusCard() {
  const [jobs, setJobs] = useState<NasStatus[]>(DEMO_STATUS);

  // TODO: 백엔드 /api/v1/admin/sync/status 연동 시 useEffect 추가
  useEffect(() => {
    // 데모 — 5초마다 진행률 약간 증가
    const t = setInterval(() => {
      setJobs((prev) =>
        prev.map((j) => {
          if (j.status !== "running") return j;
          const delta = Math.floor(j.speed_mb_per_sec * 5 * 200);
          const newDone = Math.min(j.total, j.done + delta);
          return {
            ...j,
            done: newDone,
            remaining: j.total - newDone,
            eta_seconds: newDone >= j.total ? 0 : (j.eta_seconds ?? 0) - 5,
          };
        })
      );
    }, 5000);
    return () => clearInterval(t);
  }, []);

  const toggle = (idx: number) => {
    setJobs((prev) =>
      prev.map((j, i) =>
        i === idx
          ? {
              ...j,
              status: j.status === "running" ? "paused" : "running",
              speed_mb_per_sec: j.status === "running" ? 0 : 2.4,
            }
          : j
      )
    );
  };

  return (
    <div className="border bg-white" style={{ borderColor: "var(--kbid-border)" }}>
      <div
        className="text-white px-3 py-2 text-[12px] font-bold flex items-center justify-between"
        style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
      >
        <span>NAS 다운로드 현황 (PDF 04 §1 — 이어받기)</span>
        <span className="text-[10px] opacity-90">
          {jobs.filter((j) => j.status === "running").length}건 진행 / {jobs.length}건
        </span>
      </div>
      <div className="p-3 space-y-3">
        {jobs.map((j, idx) => {
          const pct = (j.done / j.total) * 100;
          return (
            <div key={j.job_name}>
              <div className="flex items-center justify-between mb-1">
                <div className="text-[12px] font-bold" style={{ color: "var(--kbid-text-strong)" }}>
                  {j.job_name}
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  <span
                    className="px-2 py-0.5 text-white text-[10px] font-bold"
                    style={{
                      background: STATUS_COLOR[j.status],
                      borderRadius: 2,
                    }}
                  >
                    {STATUS_LABEL[j.status]}
                  </span>
                  <button
                    onClick={() => toggle(idx)}
                    className="kbid-btn-secondary"
                    style={{ padding: "2px 8px", fontSize: 11 }}
                  >
                    {j.status === "running" ? "⏸ 일시정지" : "▶ 이어받기"}
                  </button>
                </div>
              </div>
              <div
                className="relative h-5 overflow-hidden"
                style={{ background: "#E8EDF3", border: "1px solid var(--kbid-border)" }}
              >
                <div
                  className="h-full"
                  style={{
                    width: `${pct.toFixed(2)}%`,
                    background:
                      j.status === "running"
                        ? "linear-gradient(to right, #5481B8, #437194)"
                        : "#A0A8B3",
                    transition: "width 0.5s",
                  }}
                />
                <div
                  className="absolute inset-0 flex items-center justify-center font-bold text-white"
                  style={{ fontSize: 10, textShadow: "0 1px 0 rgba(0,0,0,0.3)" }}
                >
                  {pct.toFixed(2)}% · {j.done.toLocaleString()} / {j.total.toLocaleString()}
                </div>
              </div>
              <div className="flex items-center gap-3 mt-1 text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>
                <span>속도 {j.speed_mb_per_sec.toFixed(1)} MB/s</span>
                {j.eta_seconds != null && j.eta_seconds > 0 && (
                  <span>예상 {Math.round(j.eta_seconds / 60)}분</span>
                )}
                {j.last_resume_at && <span>마지막 재개 {j.last_resume_at}</span>}
                <span className="ml-auto">잔여 {j.remaining.toLocaleString()}건</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
