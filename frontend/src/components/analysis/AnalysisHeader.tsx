"use client";

import type { AnnouncementMeta } from "@/types/analysis";

interface Props {
  announcement: AnnouncementMeta | null;
}

export default function AnalysisHeader({ announcement }: Props) {
  return (
    <div className="bg-gradient-to-r from-[#2C4F8A] to-[#3358A4] text-white px-6 py-4">
      <h1 className="text-lg font-bold">낙찰분석 알리미</h1>
      <p className="text-sm text-blue-200 mt-0.5">
        {announcement
          ? announcement.org
            ? `${announcement.title} — ${announcement.org}`
            : announcement.title
          : "사정률 발생빈도와 구간분석을 통한 낙찰 예측"}
      </p>
    </div>
  );
}
