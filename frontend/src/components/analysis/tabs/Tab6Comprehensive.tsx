"use client";

/**
 * Tab6: 종합분석 (KBID 동등성 — 1차 데모 검토 §3)
 *
 * KBID PDF 4페이지 4-카드 레이아웃:
 *  - 구간정보 (예상 사정률·금액·낙찰률)
 *  - 구간 A — 빈도최대 (rate-buckets.buckets.A 상위)
 *  - 구간 B — 공백 (rate-buckets.buckets.B)
 *  - 구간 C — 차이최대 (rate-buckets.buckets.C)
 *  - 종합정보 (3가지 방법 종합 1순위 + 합치도 + 신뢰도)
 */
import type {
  AnnouncementMeta,
  AnalysisRateBucketsResponse,
  AnalysisCorrelationResponse,
  AnalysisComprehensiveResponse,
  BucketItem,
} from "@/types/analysis";

interface Props {
  announcement: AnnouncementMeta | null;
  rateBuckets: AnalysisRateBucketsResponse | null;
  correlation: AnalysisCorrelationResponse | null;
  comprehensive: AnalysisComprehensiveResponse | null;
  selectedRate: number | null;
  onRateSelect: (rate: number) => void;
}

const MODE_LABELS: Record<"A" | "B" | "C", { name: string; desc: string; color: string }> = {
  A: { name: "구간 A", desc: "빈도최대", color: "#437194" },
  B: { name: "구간 B", desc: "공백 (낮은 빈도)", color: "#8AA7C9" },
  C: { name: "구간 C", desc: "차이최대 (인접 갭)", color: "#5481B8" },
};

function BucketCard({
  mode,
  items,
  selectedRate,
  onRateSelect,
}: {
  mode: "A" | "B" | "C";
  items: BucketItem[];
  selectedRate: number | null;
  onRateSelect: (rate: number) => void;
}) {
  const info = MODE_LABELS[mode];
  const top = items[0];
  return (
    <div className="border border-gray-300 bg-white">
      <div
        className="text-white px-3 py-2 text-[12px] font-bold flex items-center justify-between"
        style={{
          background: `linear-gradient(to bottom, ${info.color}cc, ${info.color})`,
        }}
      >
        <span>
          {info.name} — {info.desc}
        </span>
        <span className="text-[10px] opacity-90">상위 {Math.min(items.length, 5)}</span>
      </div>
      {top ? (
        <div className="p-2.5 border-b border-gray-200">
          <div className="text-[10px] text-gray-500">1순위 예측</div>
          <button
            onClick={() => onRateSelect(top.rate)}
            className="text-[20px] font-extrabold text-[#437194] hover:underline"
          >
            {top.rate.toFixed(2)}%
          </button>
          <div className="text-[10px] text-gray-500 mt-1">
            점수 {top.score.toLocaleString()} · {top.side === "+" ? "↑" : top.side === "-" ? "↓" : "="}{" "}
            방향
          </div>
        </div>
      ) : (
        <div className="p-3 text-[11px] text-gray-400 text-center">데이터 없음</div>
      )}
      {items.length > 0 && (
        <table className="w-full border-collapse text-[10px]">
          <thead>
            <tr className="bg-[#E8EDF3]">
              <th className="border border-gray-300 px-1.5 py-1">순위</th>
              <th className="border border-gray-300 px-1.5 py-1">사정률</th>
              <th className="border border-gray-300 px-1.5 py-1">방향</th>
              <th className="border border-gray-300 px-1.5 py-1">점수</th>
            </tr>
          </thead>
          <tbody>
            {items.slice(0, 5).map((it, i) => {
              const isSel =
                selectedRate != null && Math.abs(it.rate - selectedRate) < 0.005;
              return (
                <tr
                  key={i}
                  onClick={() => onRateSelect(it.rate)}
                  className={`cursor-pointer ${
                    isSel ? "bg-[#FFF7ED]" : "hover:bg-blue-50"
                  }`}
                >
                  <td className="border border-gray-300 px-1.5 py-1 text-center font-bold text-[#437194]">
                    {it.rank}
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 text-center font-semibold">
                    {it.rate.toFixed(2)}%
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 text-center">
                    {it.side === "+" ? "↑" : it.side === "-" ? "↓" : "="}
                  </td>
                  <td className="border border-gray-300 px-1.5 py-1 text-center text-gray-600">
                    {it.score}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function Tab6Comprehensive({
  announcement,
  rateBuckets,
  correlation,
  comprehensive,
  selectedRate,
  onRateSelect,
}: Props) {
  const conf = correlation?.correlation.confidence;
  const confColor =
    conf?.level === "high"
      ? "#4CAF50"
      : conf?.level === "medium"
      ? "#E8913A"
      : "#9E9E9E";

  return (
    <div>
      <div className="text-[13px] font-bold text-[#437194] mb-3">
        종합분석 — KBID 4-카드 + 종합정보 (v4)
      </div>

      {/* 4-카드 그리드: 구간정보 + A + B + C — KBID 동등 */}
      <div className="grid grid-cols-4 gap-3 mb-3">
        {/* 구간정보 카드 */}
        <div className="border bg-white" style={{ borderColor: "var(--kbid-border)" }}>
          <div className="text-white px-3 py-2 text-[12px] font-bold" style={{ background: "var(--text)" }}>
            구간정보
          </div>
          <div className="p-3 space-y-2 text-[11px]">
            <div>
              <div className="text-gray-500">공고명</div>
              <div className="font-semibold truncate" title={announcement?.title}>
                {announcement?.title ?? "-"}
              </div>
            </div>
            <div>
              <div className="text-gray-500">발주기관</div>
              <div>{announcement?.org ?? "-"}</div>
            </div>
            <div>
              <div className="text-gray-500">기초금액</div>
              <div className="font-bold text-[#437194] text-[12px]">
                {announcement?.budget
                  ? `${announcement.budget.toLocaleString()}원`
                  : "-"}
              </div>
            </div>
            {comprehensive?.predicted_first_place && (
              <div className="border-t border-gray-200 pt-2">
                <div className="text-gray-500 text-[10px]">예상 1순위 낙찰</div>
                <button
                  onClick={() =>
                    onRateSelect(comprehensive.predicted_first_place!.rate)
                  }
                  className="text-[16px] font-extrabold text-[#E8913A] hover:underline"
                >
                  {comprehensive.predicted_first_place.rate.toFixed(2)}%
                </button>
                <div className="text-[10px] text-gray-600">
                  ≈ {comprehensive.predicted_first_place.amount.toLocaleString()}원
                </div>
              </div>
            )}
            {comprehensive?.confirmed_rate != null && (
              <div className="text-[10px] text-gray-500">
                확정 사정률 {comprehensive.confirmed_rate.toFixed(2)}%
              </div>
            )}
          </div>
        </div>

        {/* 구간 A / B / C 카드 */}
        <BucketCard
          mode="A"
          items={rateBuckets?.buckets.A ?? []}
          selectedRate={selectedRate}
          onRateSelect={onRateSelect}
        />
        <BucketCard
          mode="B"
          items={rateBuckets?.buckets.B ?? []}
          selectedRate={selectedRate}
          onRateSelect={onRateSelect}
        />
        <BucketCard
          mode="C"
          items={rateBuckets?.buckets.C ?? []}
          selectedRate={selectedRate}
          onRateSelect={onRateSelect}
        />

      </div>

      {/* 종합정보 row — 별도 풀폭 row (v4 KBID 동등 구조) */}
      {correlation && (
        <div className="border bg-white mb-3" style={{ borderColor: "var(--kbid-border)" }}>
          <div
            className="text-white px-4 py-2 text-[13px] font-bold"
            style={{ background: "var(--accent-warm)" }}
          >
            종합정보 — 3가지 방법 종합
          </div>
          <div className="grid grid-cols-4 gap-0">
            <div className="p-4 border-r" style={{ borderColor: "var(--kbid-border)" }}>
              <div className="text-[11px] text-gray-500 mb-1">종합 1순위</div>
              <button
                onClick={() => onRateSelect(correlation.correlation.final_top1)}
                className="text-[26px] font-extrabold text-[#437194] hover:underline"
              >
                {correlation.correlation.final_top1.toFixed(2)}%
              </button>
            </div>
            <div className="p-4 border-r" style={{ borderColor: "var(--kbid-border)" }}>
              <div className="text-[11px] text-gray-500 mb-1">예상 투찰금액</div>
              <div className="text-[18px] font-bold" style={{ color: "var(--kbid-text-strong)" }}>
                {correlation.correlation.predicted_bid_amount.toLocaleString()}원
              </div>
              <div className="text-[10px] text-gray-500 mt-1">
                기초금액 × 종합 사정률
              </div>
            </div>
            <div className="p-4 border-r" style={{ borderColor: "var(--kbid-border)" }}>
              <div className="text-[11px] text-gray-500 mb-1">합치도 (3개 방법 일치)</div>
              <div className="text-[18px] font-bold">
                {(correlation.correlation.agreement * 100).toFixed(0)}%
                <span className="text-[11px] text-gray-500 ml-1">
                  ({correlation.correlation.methods_aligned.length}/3)
                </span>
              </div>
            </div>
            <div className="p-4">
              <div className="text-[11px] text-gray-500 mb-1">신뢰도</div>
              <div className="flex items-center gap-2">
                <span
                  className="px-2.5 py-1 text-white text-[12px] font-bold"
                  style={{ backgroundColor: confColor, borderRadius: 2 }}
                >
                  {conf?.level === "high"
                    ? "높음"
                    : conf?.level === "medium"
                    ? "중간"
                    : "낮음"}{" "}
                  ({conf?.score ?? 0})
                </span>
              </div>
              <div className="text-[10px] text-gray-500 mt-2">
                표본 {correlation.correlation.sample_size.toLocaleString()}건 · 이상치{" "}
                {correlation.correlation.outliers_removed}건 제거
              </div>
              {conf && (
                <div className="text-[10px] text-gray-600 mt-1">
                  {conf.reasons.slice(0, 2).join(" · ")}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* 3가지 방법 상세 (correlation.methods) */}
      {correlation?.methods && correlation.methods.length > 0 && (
        <div className="border border-gray-300 bg-white">
          <div className="bg-gradient-to-b from-[#5481B8] to-[#437194] text-white px-3 py-2 text-[12px] font-bold">
            3가지 분석 방법 결과
          </div>
          <table className="w-full border-collapse text-[11px]">
            <thead>
              <tr className="bg-[#E8EDF3]">
                <th className="border border-gray-300 px-2 py-1 text-left">방법</th>
                <th className="border border-gray-300 px-2 py-1 text-center">1순위 사정률</th>
                <th className="border border-gray-300 px-2 py-1 text-center">점수</th>
                <th className="border border-gray-300 px-2 py-1 text-center">표본</th>
                <th className="border border-gray-300 px-2 py-1 text-center">동질성</th>
                <th className="border border-gray-300 px-2 py-1 text-center">모드</th>
                <th className="border border-gray-300 px-2 py-1 text-center">선택</th>
              </tr>
            </thead>
            <tbody>
              {correlation.methods.map((m, i) => {
                const aligned =
                  correlation.correlation.methods_aligned.includes(m.name);
                return (
                  <tr
                    key={i}
                    className={aligned ? "bg-[#FFF7ED]" : "hover:bg-blue-50"}
                  >
                    <td className="border border-gray-300 px-2 py-1">
                      {aligned && <span className="text-[#E8913A] mr-1">*</span>}
                      {m.name}
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center font-bold text-[#437194]">
                      {m.top1_rate.toFixed(4)}%
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center">
                      {m.top1_score}
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center">
                      {m.count.toLocaleString()}
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center">
                      {m.homogeneity?.toFixed(4) ?? "-"}
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center text-gray-600">
                      {m.mode ?? "-"}
                    </td>
                    <td className="border border-gray-300 px-2 py-1 text-center">
                      <button
                        onClick={() => onRateSelect(m.top1_rate)}
                        className="px-2 py-0.5 text-[10px] bg-[#437194] text-white hover:bg-[#346081]"
                      >
                        선택
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
