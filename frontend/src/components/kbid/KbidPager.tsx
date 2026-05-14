"use client";

/**
 * KBID 페이지네이션 — 처음/이전/번호/다음/마지막 + "100단위씩" 셀렉트
 */
interface Props {
  page: number;
  totalPages: number;
  pageSize: number;
  pageSizeOptions?: number[];
  onPageChange: (p: number) => void;
  onPageSizeChange?: (n: number) => void;
}

export default function KbidPager({
  page,
  totalPages,
  pageSize,
  pageSizeOptions = [20, 50, 100, 200],
  onPageChange,
  onPageSizeChange,
}: Props) {
  const start = Math.max(1, Math.min(page - 4, Math.max(1, totalPages - 9)));
  const end = Math.min(totalPages, start + 9);
  const numbers: number[] = [];
  for (let i = start; i <= end; i++) numbers.push(i);

  return (
    <div className="flex items-center justify-between py-3 px-1">
      <div className="text-[11px]" style={{ color: "var(--kbid-text-meta)" }}>
        {totalPages > 0 ? `${page} / ${totalPages} 페이지` : "—"}
      </div>
      <div className="kbid-pager">
        <button
          className="page-btn"
          onClick={() => onPageChange(1)}
          disabled={page <= 1}
        >
          «
        </button>
        <button
          className="page-btn"
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
        >
          ‹
        </button>
        {numbers.map((n) => (
          <button
            key={n}
            className={`page-btn ${n === page ? "active" : ""}`}
            onClick={() => onPageChange(n)}
          >
            {n}
          </button>
        ))}
        <button
          className="page-btn"
          onClick={() => onPageChange(Math.min(totalPages, page + 1))}
          disabled={page >= totalPages}
        >
          ›
        </button>
        <button
          className="page-btn"
          onClick={() => onPageChange(totalPages)}
          disabled={page >= totalPages}
        >
          »
        </button>
      </div>
      {onPageSizeChange && (
        <select
          className="text-[11px] border px-2 py-1"
          style={{ borderColor: "var(--kbid-border)" }}
          value={pageSize}
          onChange={(e) => onPageSizeChange(Number(e.target.value))}
        >
          {pageSizeOptions.map((n) => (
            <option key={n} value={n}>
              {n}단위씩
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
