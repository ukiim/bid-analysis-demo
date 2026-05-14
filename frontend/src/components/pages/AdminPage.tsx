"use client";

/**
 * 관리자 모니터링 페이지 — v4 KBID 톤
 */
import AmLineChart from "@/components/charts/AmLineChart";

const KPI_DATA = [
  { label: "전체 사용자", value: "1,284", unit: "명", change: "+18명 (이번주)" },
  { label: "프리미엄 구독", value: "312", unit: "명", change: "+7명 (이번주)" },
  { label: "오늘 API 호출", value: "48,291", unit: "회", change: "+12.4%" },
  { label: "수집 공고 총계", value: "382,184", unit: "건", change: "+436건 (오늘)" },
];

const PIPELINES = [
  { name: "나라장터 공고 수집", status: "success", last: "오늘 06:02", count: "347건", next: "내일 06:00" },
  { name: "국방부 공고 수집", status: "success", last: "오늘 06:15", count: "89건", next: "내일 06:00" },
  { name: "낙찰 데이터 수집", status: "success", last: "오늘 07:00", count: "284건", next: "내일 07:00" },
  { name: "예측 모델 재학습", status: "running", last: "오늘 07:30", count: "진행중", next: "-" },
  { name: "리포트 집계", status: "pending", last: "어제 23:00", count: "대기중", next: "오늘 23:00" },
];

const MODEL_ACCURACY = [
  { period: "10월", avg_rate: 2.41, min_rate: null, max_rate: 3.12 },
  { period: "11월", avg_rate: 2.28, min_rate: null, max_rate: 2.97 },
  { period: "12월", avg_rate: 2.15, min_rate: null, max_rate: 2.81 },
  { period: "1월", avg_rate: 2.03, min_rate: null, max_rate: 2.65 },
  { period: "2월", avg_rate: 1.94, min_rate: null, max_rate: 2.54 },
  { period: "3월", avg_rate: 1.87, min_rate: null, max_rate: 2.43 },
];

const USERS = [
  { name: "김영호", email: "ykim@guncorp.co.kr", plan: "프리미엄", joined: "2025.12.08", last: "오늘", queries: 342 },
  { name: "박수연", email: "sypark@daewoo.co.kr", plan: "스탠다드", joined: "2026.01.15", last: "어제", queries: 128 },
  { name: "이재원", email: "jwlee@hanshin.com", plan: "프리미엄", joined: "2025.11.20", last: "오늘", queries: 489 },
  { name: "최민준", email: "mjchoi@hyundai-eng.com", plan: "무료", joined: "2026.02.10", last: "3일 전", queries: 24 },
  { name: "정다혜", email: "dhjeong@posco.co.kr", plan: "스탠다드", joined: "2026.01.28", last: "오늘", queries: 216 },
];

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  success: { label: "정상", color: "#2B8B3C" },
  running: { label: "진행중", color: "#E8913A" },
  pending: { label: "대기중", color: "#D9342B" },
};

const PLAN_COLORS: Record<string, { bg: string; fg: string }> = {
  프리미엄: { bg: "#DCE8F6", fg: "#0E47C8" },
  스탠다드: { bg: "#DDF1DF", fg: "#2B8B3C" },
  무료: { bg: "#F5EAD0", fg: "#C56F1A" },
};

export default function AdminPage() {
  return (
    <div>
      <div
        className="bg-white border-b"
        style={{ borderColor: "var(--kbid-border)", padding: "12px 16px", marginBottom: 14 }}
      >
        <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--kbid-text-strong)" }}>
          ⚙️ 관리자 모니터링
        </h1>
        <p className="text-[12px] mt-1" style={{ color: "var(--kbid-text-meta)" }}>
          데이터 파이프라인 상태 · 예측 모델 성능 · 사용자 관리
        </p>
      </div>

      {/* KPI 4종 — KBID form-table 스타일 */}
      <div className="grid grid-cols-4 gap-0 mb-3" style={{ border: "1px solid var(--kbid-border)" }}>
        {KPI_DATA.map((k, i) => (
          <div
            key={i}
            className="p-4 bg-white"
            style={{
              borderRight: i < 3 ? "1px solid var(--kbid-border)" : undefined,
            }}
          >
            <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
              {k.label}
            </div>
            <div className="my-1">
              <span className="text-[24px] font-extrabold" style={{ color: "var(--kbid-text-strong)" }}>
                {k.value}
              </span>
              <span className="text-[12px] ml-1" style={{ color: "var(--kbid-text-meta)" }}>
                {k.unit}
              </span>
            </div>
            <div className="text-[10px]" style={{ color: "#2B8B3C", fontWeight: 600 }}>
              {k.change}
            </div>
          </div>
        ))}
      </div>

      {/* 파이프라인 + 모델 성능 */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
          >
            데이터 파이프라인 현황
          </div>
          <table className="kbid-list-table" style={{ borderTop: "none" }}>
            <thead>
              <tr>
                <th style={{ width: 40 }}>상태</th>
                <th>이름</th>
                <th>마지막 실행</th>
                <th>다음 실행</th>
              </tr>
            </thead>
            <tbody>
              {PIPELINES.map((p) => {
                const s = STATUS_LABELS[p.status];
                return (
                  <tr key={p.name}>
                    <td>
                      <span
                        className="inline-block w-2 h-2 rounded-full"
                        style={{ background: s.color }}
                      />
                    </td>
                    <td style={{ textAlign: "left", fontWeight: 600 }}>{p.name}</td>
                    <td style={{ fontSize: 11, color: "#666" }}>
                      {p.last} · {p.count}
                    </td>
                    <td style={{ fontSize: 11, color: "#666" }}>{p.next}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div>
          <div
            className="text-white px-3 py-2 text-[12px] font-bold"
            style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
          >
            예측 모델 성능 추이 (MAE / RMSE)
          </div>
          <div className="bg-white border-x border-b p-3" style={{ borderColor: "var(--kbid-border)" }}>
            <AmLineChart data={MODEL_ACCURACY} height={220} />
            <div className="grid grid-cols-2 gap-2 mt-2 text-[12px]">
              <div className="p-2 border" style={{ borderColor: "var(--kbid-border)" }}>
                <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>현재 MAE</div>
                <div className="text-[18px] font-extrabold" style={{ color: "var(--kbid-primary)" }}>
                  1.87
                </div>
              </div>
              <div className="p-2 border" style={{ borderColor: "var(--kbid-border)" }}>
                <div className="text-[10px]" style={{ color: "var(--kbid-text-meta)" }}>현재 RMSE</div>
                <div className="text-[18px] font-extrabold" style={{ color: "#E8913A" }}>
                  2.43
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 최근 가입 사용자 */}
      <div>
        <div
          className="text-white px-3 py-2 text-[12px] font-bold flex items-center justify-between"
          style={{ background: "linear-gradient(to bottom, #346081, #1E3A6B)" }}
        >
          <span>최근 가입 사용자</span>
          <button
            className="text-[11px] px-2.5 py-1"
            style={{
              background: "rgba(255,255,255,0.15)",
              color: "#fff",
              border: "1px solid rgba(255,255,255,0.3)",
            }}
          >
            전체 사용자 관리
          </button>
        </div>
        <table className="kbid-list-table" style={{ borderTop: "none" }}>
          <thead>
            <tr>
              <th>이름</th>
              <th>이메일</th>
              <th>플랜</th>
              <th>가입일</th>
              <th>마지막 접속</th>
              <th>조회 횟수</th>
            </tr>
          </thead>
          <tbody>
            {USERS.map((u) => {
              const pc = PLAN_COLORS[u.plan] ?? { bg: "#E8E8E8", fg: "#555" };
              return (
                <tr key={u.email}>
                  <td style={{ fontWeight: 700 }}>{u.name}</td>
                  <td style={{ fontFamily: "monospace", fontSize: 11 }}>{u.email}</td>
                  <td>
                    <span
                      className="inline-block px-2 py-0.5 text-[10px] font-bold"
                      style={{ background: pc.bg, color: pc.fg, borderRadius: 2 }}
                    >
                      {u.plan}
                    </span>
                  </td>
                  <td style={{ fontSize: 11, color: "#666" }}>{u.joined}</td>
                  <td style={{ fontSize: 11, color: "#666" }}>{u.last}</td>
                  <td style={{ fontWeight: 700, color: "var(--kbid-primary)" }}>
                    {u.queries.toLocaleString()}회
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
