"use client";

/**
 * 글로벌 상단 nav — v6 (ElevenLabs 톤 미니멀)
 *
 * 1단: 로고(Inter bold) + 검색(우측) + 사용자 + 로그아웃
 * 2단: 메뉴 (밑줄 active)
 *
 * KBID 169px 3단 → 88px 2단으로 단순화
 */
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { FileText, Settings, Search, LogOut, Circle } from "lucide-react";

interface Props {
  activePage: string;
  onPageChange: (page: string) => void;
}

const MENU = [
  { id: "announcements", label: "공고 통합 조회", Icon: FileText },
  { id: "admin", label: "관리자 모니터링", Icon: Settings },
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
          router.push("/login");
        }
      } else {
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
    router.push(`/?page=announcements&q=${encodeURIComponent(searchQuery)}`);
  };

  return (
    <header className="eleven-header">
      {/* 1단: 로고 + 검색 + 사용자 */}
      <div
        className="flex items-center justify-between"
        style={{
          height: 56,
          paddingLeft: "var(--space-6)",
          paddingRight: "var(--space-6)",
        }}
      >
        <div className="flex items-center" style={{ gap: "var(--space-3)" }}>
          <span
            style={{
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: "var(--text)",
            }}
          >
            입찰 인사이트
          </span>
          <span
            className="badge"
            style={{ fontSize: 10, padding: "2px 8px" }}
          >
            BETA
          </span>
        </div>

        <div
          className="flex items-center"
          style={{ gap: "var(--space-4)" }}
        >
          <form onSubmit={handleSearch}>
            <div
              className="flex items-center"
              style={{
                width: 320,
                height: 32,
                background: "var(--bg-subtle)",
                borderRadius: "var(--radius-pill)",
                padding: "0 var(--space-3)",
                gap: "var(--space-2)",
              }}
            >
              <Search size={14} color="var(--text-meta)" />
              <input
                placeholder="공고명, 발주기관 검색"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  fontSize: "var(--text-sm)",
                  color: "var(--text)",
                }}
              />
            </div>
          </form>

          <div
            className="flex items-center"
            style={{
              gap: "var(--space-2)",
              fontSize: "var(--text-xs)",
              color: "var(--text-meta)",
            }}
          >
            <Circle size={6} fill="var(--success)" color="var(--success)" />
            <span>API 정상</span>
            <span style={{ color: "var(--text-disabled)" }}>·</span>
            <span>마지막 수집 {now || "—"}</span>
          </div>

          {user && (
            <>
              <div
                className="flex items-center"
                style={{
                  gap: "var(--space-2)",
                  paddingLeft: "var(--space-3)",
                  borderLeft: "1px solid var(--border)",
                }}
              >
                <span style={{ fontSize: "var(--text-sm)", fontWeight: 500 }}>
                  {user.name}
                </span>
                {user.plan && (
                  <span className="badge">{user.plan}</span>
                )}
              </div>
              <button
                onClick={handleLogout}
                className="btn-chip"
                title="로그아웃"
              >
                <LogOut size={12} />
                로그아웃
              </button>
            </>
          )}
        </div>
      </div>

      {/* 2단: 메뉴 (밑줄 active) */}
      <nav
        className="flex items-center"
        style={{
          height: 44,
          paddingLeft: "var(--space-6)",
          paddingRight: "var(--space-6)",
          gap: "var(--space-2)",
          borderTop: "1px solid var(--border)",
        }}
      >
        {MENU.map((m) => {
          const active = activePage === m.id;
          return (
            <button
              key={m.id}
              onClick={() => onPageChange(m.id)}
              className="flex items-center"
              style={{
                height: 44,
                padding: "0 var(--space-4)",
                gap: "var(--space-2)",
                background: "transparent",
                border: "none",
                borderBottom: active
                  ? "2px solid var(--text)"
                  : "2px solid transparent",
                color: active ? "var(--text)" : "var(--text-meta)",
                fontSize: "var(--text-sm)",
                fontWeight: active ? 600 : 500,
                cursor: "pointer",
                marginBottom: -1,
                transition: "color 80ms ease, border-color 80ms ease",
              }}
            >
              <m.Icon size={14} />
              {m.label}
            </button>
          );
        })}
      </nav>
    </header>
  );
}
