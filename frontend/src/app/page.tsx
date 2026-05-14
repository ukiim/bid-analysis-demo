"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import Footer from "@/components/layout/Footer";
import AnnouncementsPage from "@/components/pages/AnnouncementsPage";
import AdminPage from "@/components/pages/AdminPage";

// v5 — PDF 정합화: 공고화면 + 관리자만 (예측·통계 제거)
export default function Home() {
  const sp = useSearchParams();
  const [page, setPage] = useState(sp.get("page") ?? "announcements");
  useEffect(() => {
    const p = sp.get("page");
    if (p && p !== page) setPage(p);
  }, [sp, page]);

  const renderPage = () => {
    switch (page) {
      case "announcements":
        return <AnnouncementsPage />;
      case "admin":
        return <AdminPage />;
      default:
        return <AnnouncementsPage />;
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--kbid-page-bg)" }}>
      <TopNav activePage={page} onPageChange={setPage} />
      <main className="flex-1 max-w-[1440px] w-full mx-auto" style={{ padding: "24px 24px" }}>
        {renderPage()}
      </main>
      <Footer />
    </div>
  );
}
