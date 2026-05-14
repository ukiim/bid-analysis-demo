"use client";

/**
 * KBID 상단 nav — 사이드바 대체 (v3 Phase 2)
 * kbid.co.kr 실 사이트 헤더 모방
 *
 *  - 1차 영역: 로고 (좌) + 검색 + 로그인 상태 (우)
 *  - 2차 영역: 가로 메뉴 (공사입찰 / 분석 / 통계 / 관리자)
 */
import { useEffect, useState } from "react";

interface Props {
  activePage: string;
  onPageChange: (page: string) => void;
}

const MENU = [
  { id: "announcements", label: "공사입찰", icon: "📋" },
  { id: "prediction", label: "사정률 예측", icon: "📈" },
  { id: "statistics", label: "통계 리포트", icon: "📊" },
  { id: "admin", label: "관리자 모니터링", icon: "⚙️" },
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
          // JWT payload (base64 — middle segment)
          const payload = JSON.parse(atob(token.split(".")[1]));
          setUser({ name: "관리자", plan: "프리미엄" });
        } catch {
          /* ignore */
        }
      }
    }
  }, []);

  return (
    <header className="kbid-topnav border-b border-[#08367A]">
      {/* 1차 영역: 로고 + 우측 상태 */}
      <div
        className="flex items-center justify-between px-6"
        style={{ height: 56, background: "var(--kbid-header-bg)" }}
      >
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <span
              className="font-extrabold text-[18px] tracking-tight"
              style={{ color: "#ffffff", letterSpacing: "-0.02em" }}
            >
              입찰 인사이트
            </span>
            <span
              className="text-[11px] font-semibold px-2 py-0.5 rounded"
              style={{ background: "rgba(255,255,255,0.15)", color: "#cfdbeb" }}
            >
              KBID 동등 UI
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4 text-[12px] text-white/90">
          <span className="inline-flex items-center gap-1">
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "#5BE38F" }}
            />
            API 정상
          </span>
          <span className="text-white/70">마지막 수집 {now || "—"}</span>
          {user && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-white/10">
              <span className="font-bold">{user.name}</span>
              {user.plan && (
                <span className="text-[10px] text-white/80">({user.plan})</span>
              )}
            </span>
          )}
        </div>
      </div>

      {/* 2차 영역: 메뉴 */}
      <nav
        className="kbid-topnav flex items-center px-3"
        style={{ background: "var(--kbid-subheader-bg)" }}
      >
        {MENU.map((m) => (
          <button
            key={m.id}
            onClick={() => onPageChange(m.id)}
            className={`menu-item ${activePage === m.id ? "active" : ""}`}
            style={{ background: activePage === m.id ? "rgba(0,0,0,0.18)" : "transparent" }}
          >
            <span className="mr-1.5">{m.icon}</span>
            {m.label}
          </button>
        ))}
      </nav>
    </header>
  );
}
