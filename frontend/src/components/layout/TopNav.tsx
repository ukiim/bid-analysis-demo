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
import { useRouter } from "next/navigation";

interface Props {
  activePage: string;
  onPageChange: (page: string) => void;
}

// v5 — PDF 정합화: 메뉴 2개로 축소 (공고 + 관리자)
const MENU = [
  { id: "announcements", label: "공고 통합 조회", icon: "📋" },
  { id: "admin", label: "관리자 모니터링", icon: "⚙️" },
];

// v5 — 빠른 카테고리 간소화 (공사·용역 강조)
const QUICK_LINKS = [
  { label: "공사입찰", color: "#0E47C8" },
  { label: "용역입찰", color: "#6F2B96" },
];

export default function TopNav({ activePage, onPageChange }: Props) {
  const router = useRouter();
  const [user, setUser] = useState<{ name: string; plan?: string } | null>(null);
  const [now, setNow] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

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
          const payload = JSON.parse(atob(token.split(".")[1]));
          // exp 만료 검사 (epoch 초)
          if (payload.exp && payload.exp * 1000 < Date.now()) {
            localStorage.removeItem("token");
            router.push("/login");
            return;
          }
          const stored = localStorage.getItem("user");
          if (stored) {
            try {
              const u = JSON.parse(stored);
              setUser({ name: u.name ?? "사용자", plan: u.plan });
            } catch {
              setUser({ name: "사용자" });
            }
          } else {
            setUser({ name: "관리자", plan: "프리미엄" });
          }
        } catch {
          /* invalid token — redirect */
          router.push("/login");
        }
      } else {
        // 토큰 없음 → 로그인 페이지
        router.push("/login");
      }
    }
  }, [router]);

  const handleLogout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    router.push("/login");
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    // 공고 페이지로 이동 + keyword 쿼리
    router.push(`/?page=announcements&q=${encodeURIComponent(searchQuery)}`);
  };

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
          <form onSubmit={handleSearch}>
            <input
              placeholder="🔍 공고명, 발주기관 검색 (Enter)"
              className="text-[12px] px-3 py-1"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: 280,
                background: "rgba(255,255,255,0.95)",
                color: "#333",
                border: "1px solid rgba(255,255,255,0.3)",
              }}
            />
          </form>
          <span className="inline-flex items-center gap-1">
            <span
              className="inline-block w-1.5 h-1.5 rounded-full"
              style={{ background: "#5BE38F" }}
            />
            API 정상
          </span>
          <span style={{ color: "rgba(255,255,255,0.7)" }}>마지막 수집 {now || "—"}</span>
          {user && (
            <>
              <span
                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded"
                style={{ background: "rgba(255,255,255,0.1)" }}
              >
                <span className="font-bold">{user.name}</span>
                {user.plan && (
                  <span className="text-[10px]" style={{ color: "rgba(255,255,255,0.8)" }}>
                    ({user.plan})
                  </span>
                )}
              </span>
              <button
                onClick={handleLogout}
                className="text-[11px] px-2.5 py-1"
                style={{
                  background: "rgba(255,255,255,0.12)",
                  color: "#ffffff",
                  border: "1px solid rgba(255,255,255,0.25)",
                  borderRadius: 2,
                }}
                title="로그아웃"
              >
                ⏏ 로그아웃
              </button>
            </>
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
