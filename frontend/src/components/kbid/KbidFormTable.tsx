"use client";

/**
 * KBID 폼-테이블 컴포넌트 — 라벨(좌) + 셀(우) 2열 그리드를 N행 만큼.
 * kbid-tokens.css의 .kbid-form-table 클래스 활용.
 *
 * 사용 예:
 *   <KbidFormTable rows={[
 *     [{ label: "공고명", colSpan: 3, content: <input /> }, { label: "공고번호", content: <input readOnly /> }],
 *     [{ label: "기간", colSpan: 3, content: <DateRange /> }],
 *   ]} />
 *
 * row는 2열 또는 4열 (라벨/셀이 두 쌍) 구조를 지원.
 */
import type { ReactNode } from "react";

export interface KbidFormCell {
  label: string;
  content: ReactNode;
  /** 셀 전체가 차지할 td 개수 (라벨 제외). 기본 1. */
  colSpan?: number;
  /** 라벨 폭 (px). 기본 110. */
  labelWidth?: number;
}

interface Props {
  rows: KbidFormCell[][];
  /** Form-table 총 컬럼 수 (라벨+셀 짝 — 기본 4 = 2쌍). */
  columns?: 2 | 4;
  /** 표 위쪽 강조 라인 색 */
  topBorderColor?: string;
}

export default function KbidFormTable({
  rows,
  columns = 4,
  topBorderColor = "var(--kbid-primary)",
}: Props) {
  return (
    <table
      className="kbid-form-table"
      style={{ borderTop: `2px solid ${topBorderColor}` }}
    >
      <colgroup>
        {/* 라벨 + 셀 ... 라벨 + 셀 (총 columns 쌍) */}
        {Array.from({ length: columns }, (_, i) =>
          i % 2 === 0 ? (
            <col key={i} style={{ width: 110 }} />
          ) : (
            <col key={i} />
          )
        )}
      </colgroup>
      <tbody>
        {rows.map((row, rIdx) => (
          <tr key={rIdx}>
            {row.flatMap((cell, cIdx) => [
              <th
                key={`l${cIdx}`}
                style={cell.labelWidth ? { width: cell.labelWidth } : undefined}
              >
                {cell.label}
              </th>,
              <td
                key={`c${cIdx}`}
                colSpan={cell.colSpan ?? 1}
                style={{ padding: "6px 10px" }}
              >
                {cell.content}
              </td>,
            ])}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
