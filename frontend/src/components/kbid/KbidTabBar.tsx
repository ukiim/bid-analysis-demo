"use client";

/**
 * KBID 4-탭 스타일 탭바 (kbid-tokens.css의 .kbid-tab 활용)
 * — 공고화면 상단: 법령공고/결과공고/지사공고/전체공고
 * — 분석페이지 탭바: 사정률 그래프/예가빈도/발생빈도/종합분석
 */

interface TabItem<K extends string = string> {
  key: K;
  label: string;
  badge?: string | number;
}

interface Props<K extends string = string> {
  items: TabItem<K>[];
  activeKey: K;
  onChange: (key: K) => void;
  className?: string;
}

export default function KbidTabBar<K extends string = string>({
  items,
  activeKey,
  onChange,
  className = "",
}: Props<K>) {
  return (
    <div className={`kbid-tab-bar ${className}`}>
      {items.map((it) => (
        <button
          key={it.key}
          onClick={() => onChange(it.key)}
          className={`kbid-tab ${it.key === activeKey ? "active" : ""}`}
          style={{
            marginRight: "-1px",
            borderBottom: it.key === activeKey ? "none" : "1px solid var(--kbid-border)",
          }}
        >
          {it.label}
          {it.badge != null && (
            <span
              className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded"
              style={{
                background:
                  it.key === activeKey ? "rgba(255,255,255,0.25)" : "var(--kbid-accent-orange)",
                color: "#ffffff",
              }}
            >
              {it.badge}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
