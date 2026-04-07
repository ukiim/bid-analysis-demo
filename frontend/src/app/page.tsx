"use client";

import { useState } from "react";
import Sidebar from "@/components/layout/Sidebar";
import AnnouncementsPage from "@/components/pages/AnnouncementsPage";
import PredictionPage from "@/components/pages/PredictionPage";
import StatisticsPage from "@/components/pages/StatisticsPage";
import AdminPage from "@/components/pages/AdminPage";

const PAGE_LABELS: Record<string, { icon: string; label: string }> = {
  announcements: { icon: "📋", label: "공고 통합 조회" },
  prediction: { icon: "📈", label: "사정률 예측" },
  statistics: { icon: "📊", label: "통계 리포트" },
  admin: { icon: "⚙️", label: "관리자 모니터링" },
};

export default function Home() {
  const [page, setPage] = useState("announcements");
  const current = PAGE_LABELS[page];

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
    <div className="flex h-screen overflow-hidden">
      <Sidebar activePage={page} onPageChange={setPage} />
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* 상단바 */}
        <header className="h-14 bg-white border-b border-border flex items-center px-6 justify-between flex-shrink-0">
          <div className="text-[15px] font-semibold">
            {current.icon} {current.label}
          </div>
          <div className="flex items-center gap-3">
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-green-50 text-green-600">
              ● API 정상
            </span>
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-blue-50 text-primary">
              마지막 수집: 오늘 07:00
            </span>
            <button className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[13px] font-semibold bg-primary text-white hover:bg-primary-dark transition">
              🔄 수동 수집
            </button>
          </div>
        </header>

        {/* 컨텐츠 */}
        <main className="flex-1 overflow-y-auto p-6">{renderPage()}</main>
      </div>
    </div>
  );
}
