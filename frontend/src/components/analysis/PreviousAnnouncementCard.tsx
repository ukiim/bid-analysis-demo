"use client";

/**
 * 바로 이전 결과공고 갭 비교 카드 — PDF 04 §2
 *
 * /api/v1/announcements/{id}/previous 응답 활용
 */
import { useEffect, useState } from "react";

interface PreviousResult {
  prev: {
    id: string;
    title: string;
    announced_at: string | null;
    base_amount: number | null;
    category: string;
    industry_code: string | null;
    region: string | null;
    ordering_org_name: string;
    result: {
      winning_amount: number | null;
      assessment_rate: number | null;
      first_place_rate: number | null;
      first_place_amount: number | null;
      winning_company: string | null;
    } | null;
  } | null;
  fallback_used: string;
}

interface Props {
  announcementId: string;
  currentRate?: number | null;
}

function authHeaders(): HeadersInit {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("token") : null;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export default function PreviousAnnouncementCard({
  announcementId,
  currentRate,
}: Props) {
  const [data, setData] = useState<PreviousResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!announcementId) return;
    setLoading(true);
    fetch(`/api/v1/announcements/${announcementId}/previous`, {
      headers: authHeaders(),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [announcementId]);

  if (loading) {
    return (
      <div className="border bg-white p-3 text-[12px]" style={{ borderColor: "var(--kbid-border)" }}>
        이전 공고 비교 로딩 중...
      </div>
    );
  }

  if (!data?.prev) {
    return (
      <div
        className="border bg-white"
        style={{ borderColor: "var(--kbid-border)" }}
      >
        <div
          className="text-white px-3 py-1.5 text-[11px] font-bold"
          style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
        >
          바로 이전 결과공고 갭 비교 (PDF 04 §2)
        </div>
        <div className="p-3 text-[12px] text-gray-500 text-center">
          비교 가능한 이전 공고 없음
        </div>
      </div>
    );
  }

  const prev = data.prev;
  const result = prev.result;
  const gap =
    currentRate != null && result?.first_place_rate != null
      ? currentRate - result.first_place_rate
      : null;

  return (
    <div
      className="border bg-white"
      style={{ borderColor: "var(--kbid-border)" }}
    >
      <div
        className="text-white px-3 py-1.5 text-[11px] font-bold flex items-center justify-between"
        style={{ background: "linear-gradient(to bottom, #5481B8, #437194)" }}
      >
        <span>바로 이전 결과공고 갭 비교 (PDF 04 §2)</span>
        <span className="text-[10px] opacity-90">
          fallback: {data.fallback_used}
        </span>
      </div>
      <div className="p-3 text-[11px] space-y-2">
        <div>
          <div className="text-gray-500 text-[10px]">이전 공고</div>
          <div className="font-semibold truncate" style={{ color: "var(--kbid-text-strong)" }}>
            {prev.title}
          </div>
          <div className="text-[10px] text-gray-500 mt-0.5">
            {prev.ordering_org_name} · {prev.announced_at ?? "-"}
            {prev.region && ` · ${prev.region}`}
          </div>
        </div>
        {result && (
          <div className="grid grid-cols-2 gap-2 border-t pt-2" style={{ borderColor: "var(--kbid-border)" }}>
            <div>
              <div className="text-[10px] text-gray-500">이전 사정률</div>
              <div className="font-bold" style={{ color: "var(--kbid-primary)" }}>
                {result.assessment_rate?.toFixed(4) ?? "-"}%
              </div>
            </div>
            <div>
              <div className="text-[10px] text-gray-500">이전 1순위</div>
              <div className="font-bold" style={{ color: "#E8913A" }}>
                {result.first_place_rate?.toFixed(4) ?? "-"}%
              </div>
            </div>
          </div>
        )}
        {gap != null && (
          <div className="border-t pt-2" style={{ borderColor: "var(--kbid-border)" }}>
            <div className="text-[10px] text-gray-500">현재 선택 사정률과 갭</div>
            <div
              className="text-[15px] font-extrabold"
              style={{
                color: Math.abs(gap) < 0.1 ? "#2B8B3C" : "#E8913A",
              }}
            >
              {gap > 0 ? "+" : ""}
              {gap.toFixed(4)}%
            </div>
            <div className="text-[10px] text-gray-500 mt-0.5">
              {Math.abs(gap) < 0.1
                ? "✓ 이전 1순위와 매우 유사"
                : Math.abs(gap) < 0.5
                ? "근접"
                : "차이 큼"}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
