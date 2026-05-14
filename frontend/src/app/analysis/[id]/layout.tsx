"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import Footer from "@/components/layout/Footer";

// v3 — 분석페이지에도 동일한 TopNav + Footer (KBID 동등 글로벌 레이아웃)
export default function AnalysisLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [active, setActive] = useState("announcements");

  // 메뉴 클릭 시 홈으로 라우팅 (SPA 페이지 전환은 / 안에서만 가능)
  const handlePage = (page: string) => {
    setActive(page);
    // page 변경은 / 로 가서 처리 (root page.tsx 가 SPA 상태 관리)
    router.push(`/?page=${page}`);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--kbid-page-bg)" }}>
      <TopNav activePage={active} onPageChange={handlePage} />
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-5 py-5">
        {children}
      </main>
      <Footer />
    </div>
  );
}
