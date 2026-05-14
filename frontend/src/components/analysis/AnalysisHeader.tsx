"use client";

import type { AnnouncementMeta } from "@/types/analysis";

interface Props {
  announcement: AnnouncementMeta | null;
}

// v3 — KBID 동등 헤더: 진한 인디고 BG + 흰 텍스트, 라운드 없음
export default function AnalysisHeader({ announcement }: Props) {
  return (
    <div
      style={{
        background: "var(--kbid-primary)",
        borderBottom: "1px solid var(--kbid-primary-border)",
        padding: "12px 16px",
        color: "#ffffff",
      }}
    >
      <h1
        style={{
          fontSize: 16,
          fontWeight: 700,
          marginBottom: 2,
          letterSpacing: "-0.01em",
        }}
      >
        낙찰분석 알리미
      </h1>
      <p style={{ fontSize: 12, color: "rgba(255,255,255,0.78)" }}>
        {announcement
          ? announcement.org
            ? `${announcement.title} — ${announcement.org}`
            : announcement.title
          : "사정률 발생빈도와 구간분석을 통한 낙찰 예측"}
      </p>
    </div>
  );
}
