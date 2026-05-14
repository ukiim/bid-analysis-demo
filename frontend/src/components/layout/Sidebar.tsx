"use client";

import { cn } from "@/lib/utils";

interface NavItem {
  id: string;
  label: string;
  icon: string;
  section: string;
}

const NAV_ITEMS: NavItem[] = [
  { id: "announcements", label: "공고 통합 조회", icon: "[F]", section: "데이터 조회" },
  { id: "prediction", label: "사정률 예측", icon: "[L]", section: "예측 분석" },
  { id: "statistics", label: "통계 리포트", icon: "[B]", section: "예측 분석" },
  { id: "admin", label: "관리자 모니터링", icon: "[S]", section: "시스템 관리" },
];

interface SidebarProps {
  activePage: string;
  onPageChange: (page: string) => void;
}

export default function Sidebar({ activePage, onPageChange }: SidebarProps) {
  const sections = Array.from(new Set(NAV_ITEMS.map((item) => item.section)));

  return (
    <aside className="w-[260px] bg-secondary flex flex-col flex-shrink-0 overflow-y-auto">
      {/* 로고 */}
      <div className="px-5 py-5 border-b border-white/[0.08]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-base">
            📡
          </div>
          <div>
            <div className="text-[15px] font-bold text-white">입찰 인사이트</div>
            <div className="text-[11px] text-white/45">조달 입찰 분석 플랫폼</div>
          </div>
        </div>
      </div>

      {/* 네비게이션 */}
      {sections.map((section) => (
        <div key={section} className="px-3 pt-4 pb-2">
          <div className="text-[10px] font-semibold text-white/35 uppercase tracking-wider px-2 mb-1.5">
            {section}
          </div>
          {NAV_ITEMS.filter((item) => item.section === section).map((item) => (
            <button
              key={item.id}
              onClick={() => onPageChange(item.id)}
              className={cn(
                "flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-[13.5px] font-medium transition-all mb-0.5 text-left",
                activePage === item.id
                  ? "bg-primary text-white"
                  : "text-white/65 hover:bg-white/[0.08] hover:text-white"
              )}
            >
              <span className="text-[15px] w-[18px] text-center">{item.icon}</span>
              {item.label}
            </button>
          ))}
        </div>
      ))}

      {/* 하단 사용자 */}
      <div className="mt-auto p-4 border-t border-white/[0.08]">
        <div className="flex items-center gap-2.5 p-2.5 rounded-lg bg-white/[0.06]">
          <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center text-xs font-bold text-white flex-shrink-0">
            김
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white">김영호</div>
            <div className="text-[11px] text-white/45">프리미엄 플랜</div>
          </div>
        </div>
      </div>
    </aside>
  );
}
