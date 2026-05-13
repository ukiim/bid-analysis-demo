"use client";

import { type ReactNode } from "react";

interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

interface Props {
  tabs: Tab[];
  activeTab: string;
  onTabChange: (key: string) => void;
}

export default function AnalysisTabs({ tabs, activeTab, onTabChange }: Props) {
  const active = tabs.find((t) => t.key === activeTab);

  return (
    <div className="mx-4 mt-3">
      {/* Tab buttons */}
      <div className="flex">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => onTabChange(tab.key)}
            className={`px-5 py-2.5 text-[12px] font-bold border border-b-0 border-gray-300 ${
              activeTab === tab.key
                ? "bg-gradient-to-b from-[#4A7ABF] to-[#3358A4] text-white"
                : "bg-[#E8EDF3] text-gray-600 hover:bg-[#D0D8E4]"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {/* Tab content */}
      <div className="bg-white border border-gray-300 p-4 min-h-[400px]">
        {active?.content}
      </div>
    </div>
  );
}
