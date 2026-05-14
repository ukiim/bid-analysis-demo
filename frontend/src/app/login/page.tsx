"use client";

/**
 * KBID 동등 로그인 페이지 — kbid.co.kr 헤더 로그인 폼 동등 톤
 */
import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("admin@bidinsight.kr");
  const [password, setPassword] = useState("demo1234");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e?: React.FormEvent) => {
    e?.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({ username, password });
      const res = await fetch(`/api/v1/auth/login?${params.toString()}`, {
        method: "POST",
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      const data = await res.json();
      if (data.access_token) {
        localStorage.setItem("token", data.access_token);
        localStorage.setItem("user", JSON.stringify(data.user ?? {}));
        router.push("/");
      } else {
        throw new Error("토큰을 받지 못했습니다");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "로그인 실패");
    } finally {
      setLoading(false);
    }
  };

  const handleDemoLogin = (role: "admin" | "viewer") => {
    if (role === "admin") {
      setUsername("admin@bidinsight.kr");
      setPassword("demo1234");
    } else {
      setUsername("viewer@bidinsight.kr");
      setPassword("demo1234");
    }
    // 다음 tick 에서 자동 제출
    setTimeout(() => handleLogin(), 50);
  };

  return (
    <div
      className="min-h-screen flex items-center justify-center"
      style={{
        background: "linear-gradient(to bottom, #F4F7FA, #E8EDF3)",
        fontFamily: "var(--kbid-font-family)",
      }}
    >
      <div
        className="bg-white shadow-xl"
        style={{ width: 420, border: "1px solid var(--kbid-border)" }}
      >
        {/* KBID 헤더 톤 */}
        <div
          className="text-white px-6 py-4"
          style={{ background: "var(--kbid-header-bg)" }}
        >
          <div className="text-[20px] font-extrabold tracking-tight">
            입찰 인사이트
          </div>
          <div className="text-[11px] mt-0.5" style={{ color: "rgba(255,255,255,0.8)" }}>
            공공데이터 기반 입찰가 산정 · 사정률 분석 (KBID 동등 UI)
          </div>
        </div>

        <form onSubmit={handleLogin} className="p-6">
          <div className="text-[13px] font-bold mb-4" style={{ color: "var(--kbid-text-strong)" }}>
            🔐 로그인
          </div>

          {error && (
            <div
              className="mb-3 px-3 py-2 text-[12px]"
              style={{
                background: "#FFE5E0",
                border: "1px solid #D9342B",
                color: "#A8231D",
              }}
            >
              ⚠ {error}
            </div>
          )}

          <table className="kbid-form-table mb-4">
            <tbody>
              <tr>
                <th style={{ width: 80 }}>아이디</th>
                <td>
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    style={{ width: "100%", height: 30 }}
                    autoComplete="username"
                  />
                </td>
              </tr>
              <tr>
                <th>비밀번호</th>
                <td>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    style={{ width: "100%", height: 30 }}
                    autoComplete="current-password"
                  />
                </td>
              </tr>
            </tbody>
          </table>

          <button
            type="submit"
            disabled={loading}
            className="kbid-btn-primary w-full"
            style={{ height: 38, fontSize: 14, opacity: loading ? 0.6 : 1 }}
          >
            {loading ? "로그인 중..." : "로그인"}
          </button>

          <div className="my-4 flex items-center gap-3 text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
            <div className="flex-1 h-px" style={{ background: "var(--kbid-border)" }} />
            <span>데모 빠른 로그인</span>
            <div className="flex-1 h-px" style={{ background: "var(--kbid-border)" }} />
          </div>

          <div className="grid grid-cols-2 gap-2">
            <button
              type="button"
              onClick={() => handleDemoLogin("admin")}
              className="kbid-btn-secondary"
              style={{ padding: "8px 12px" }}
            >
              👤 관리자 (admin)
            </button>
            <button
              type="button"
              onClick={() => handleDemoLogin("viewer")}
              className="kbid-btn-secondary"
              style={{ padding: "8px 12px" }}
            >
              👁️ 조회자 (viewer)
            </button>
          </div>

          <div className="mt-4 text-[11px] text-center" style={{ color: "var(--kbid-text-meta)" }}>
            데모 계정: <code className="font-mono">admin@bidinsight.kr / demo1234</code>
          </div>
        </form>

        <div
          className="px-6 py-3 text-[11px] text-center"
          style={{ background: "#33363E", color: "#9CA0A8" }}
        >
          Copyright © 2026 입찰 인사이트 · 고객센터 1644-3550
        </div>
      </div>
    </div>
  );
}
