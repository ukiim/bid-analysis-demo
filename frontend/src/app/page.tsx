"use client";

import { useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import TopNav from "@/components/layout/TopNav";
import Footer from "@/components/layout/Footer";
import AnnouncementsPage from "@/components/pages/AnnouncementsPage";
import PredictionPage from "@/components/pages/PredictionPage";
import StatisticsPage from "@/components/pages/StatisticsPage";
import AdminPage from "@/components/pages/AdminPage";

// v3 — KBID UI 전면 교체: Sidebar 제거, TopNav + Footer 도입
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
      case "prediction":
        return <PredictionPage />;
      case "statistics":
        return <StatisticsPage />;
      case "admin":
        return <AdminPage />;
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--kbid-page-bg)" }}>
      <TopNav activePage={page} onPageChange={setPage} />
      <main className="flex-1 max-w-[1600px] w-full mx-auto px-5 py-5">
        {renderPage()}
      </main>
      <Footer />
    </div>
  );
}
