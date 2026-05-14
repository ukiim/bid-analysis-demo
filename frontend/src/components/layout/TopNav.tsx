"use client";

/**
 * KBID 상단 nav — v4 (3단 169px — KBID 실 사이트 동일 높이)
 *
 *  1차 56px: 로고 + 우측 상태 (사용자/로그인폼)
 *  2차 70px: 카테고리 빠른 진입 (공사입찰/용역입찰/물품입찰 등)
 *  3차 43px: 메인 메뉴 (홈/공고/사정률/통계/관리자)
 *
 * 총 약 169px — kbid.co.kr 헤더와 동일.
 */
import { useEffect, useState } from "react";

interface Props {
  activePage: string;
  onPageChange: (page: string) => void;
}

const MENU = [
  { id: "announcements", label: "공고 통합 조회", icon: "📋" },
  { id: "prediction", label: "사정률 예측", icon: "📈" },
  { id: "statistics", label: "통계 리포트", icon: "📊" },
  { id: "admin", label: "관리자 모니터링", icon: "⚙️" },
];

const QUICK_LINKS = [
  { label: "공사입찰", color: "#0E47C8" },
  { label: "용역입찰", color: "#6F2B96" },
  { label: "물품입찰", color: "#2B8B3C" },
  { label: "맞춤서비스", color: "#E8913A" },
  { label: "분석알리미", color: "#D9342B" },
  { label: "낙찰결과", color: "#346081" },
];

export default function TopNav({ activePage, onPageChange }: Props) {
  const [user, setUser] = useState<{ name: string; plan?: string } | null>(null);
  const [now, setNow] = useState("");

  useEffect(() => {
    setNow(
      new Date().toLocaleString("ko-KR", {
        month: "numeric",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    );
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("token");
      if (token) {
        try {
          JSON.parse(atob(token.split(".")[1]));
          setUser({ name: "관리자", plan: "프리미엄" });
        } catch {
          /* ignore */
        }
      }
    }
  }, []);

  return (
    <header style={{ borderBottom: "1px solid #08367A" }}>
      {/* 1차 영역 — 로고 + 검색·상태 */}
      <div
        className="flex items-center justify-between px-6"
        style={{ height: 56, background: "var(--kbid-header-bg)" }}
      >
        <div className="flex items-center gap-3">
          <div
            className="font-extrabold tracking-tight"
            style={{
              color: "#ffffff",
              fontSize: 22,
              letterSpacing: "-0.03em",
            }}
          >
            입찰 인사이트
          </div>
          <span
            className="text-[11px] font-semibold px-2 py-0.5 rounded"
            style={{ background: "rgba(255,255,255,0.15)", color: "#cfdbeb" }}
          >
            KBID 동등 UI
          </span>
        </div>
        <div className="flex items-center gap-4 text-[12px]" style={{ color: "rgba(255,255,255,0.92)" }}>
          <input
            placeholder="🔍 공고명, 발주기관 검색"
            className="text-[12px] px-3 py-1"
            style={{
              width: 280,
              background: "rgba(255,255,255,0.95)",
              color: "#333",
              border: "1px solid rgba(255,255,255,0.3)",
            }}
          />
          <span className="inline-flex items-center gap-1">
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "#5BE38F" }}
            />
            API 정상
          </span>
          <span style={{ color: "rgba(255,255,255,0.7)" }}>마지막 수집 {now || "—"}</span>
          {user && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded" style={{ background: "rgba(255,255,255,0.1)" }}>
              <span className="font-bold">{user.name}</span>
              {user.plan && (
                <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.8)" }}>
                  ({user.plan})
                </span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* 2차 영역 — 빠른 진입 카테고리 (KBID 동일 디자인) */}
      <div
        className="flex items-center px-6 gap-1"
        style={{
          height: 70,
          background: "linear-gradient(to bottom, #F4F7FA, #E8EDF3)",
          borderTop: "1px solid #B0B8C2",
          borderBottom: "1px solid #B0B8C2",
        }}
      >
        {QUICK_LINKS.map((q) => (
          <button
            key={q.label}
            className="px-4 py-2 text-[13px] font-bold transition-colors"
            style={{
              background: "#ffffff",
              border: "1px solid #C8CED6",
              borderTop: `3px solid ${q.color}`,
              color: q.color,
              minWidth: 96,
              height: 52,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {q.label}
          </button>
        ))}
        <div className="flex-1" />
        <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
          공공데이터 G2B · 국방부 OpenAPI 통합 분석 · 사정률 예측
        </div>
      </div>

      {/* 3차 영역 — 메인 메뉴 */}
      <nav
        className="kbid-topnav flex items-center px-3"
        style={{ background: "var(--kbid-subheader-bg)", height: 43 }}
      >
        {MENU.map((m) => (
          <button
            key={m.id}
            onClick={() => onPageChange(m.id)}
            className={`menu-item ${activePage === m.id ? "active" : ""}`}
            style={{
              background: activePage === m.id ? "rgba(0,0,0,0.18)" : "transparent",
              height: 43,
            }}
          >
            <span className="mr-1.5">{m.icon}</span>
            {m.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
