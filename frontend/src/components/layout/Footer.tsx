"use client";

/**
 * KBID 풋터 — 사이트 정보·고객센터·저작권
 */
export default function Footer() {
  return (
    <footer
      className="mt-10 border-t border-[#C8CED6]"
      style={{ background: "#33363E", color: "#9CA0A8" }}
    >
      <div className="px-6 py-5 flex items-center justify-between text-[12px]">
        <div className="flex items-center gap-4">
          <span className="font-bold text-white text-[13px]">입찰 인사이트</span>
          <span>공공데이터 기반 입찰가 산정 · 사정률 분석 플랫폼</span>
        </div>
        <div className="flex items-center gap-5">
          <span>고객센터 1644-3550 (평일 09:00~18:00)</span>
          <span>이용약관 · 개인정보처리방침</span>
        </div>
      </div>
      <div
        className="px-6 py-3 text-[11px] text-center"
        style={{ background: "#26282E", color: "#7B8088" }}
      >
        Copyright © 2026 입찰 인사이트. All rights reserved.
      </div>
    </footer>
  );
}
