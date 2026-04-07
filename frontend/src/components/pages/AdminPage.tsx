"use client";

import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";

const KPI_DATA = [
  { label: "전체 사용자", value: "1,284명", change: "+18명 (이번주)" },
  { label: "프리미엄 구독", value: "312명", change: "+7명 (이번주)" },
  { label: "오늘 API 호출", value: "48,291회", change: "+12.4%" },
  { label: "수집 공고 총계", value: "382,184건", change: "+436건 (오늘)" },
];

const PIPELINES = [
  { name: "나라장터 공고 수집", status: "success", last: "오늘 06:02", count: "347건", next: "내일 06:00" },
  { name: "국방부 공고 수집", status: "success", last: "오늘 06:15", count: "89건", next: "내일 06:00" },
  { name: "낙찰 데이터 수집", status: "success", last: "오늘 07:00", count: "284건", next: "내일 07:00" },
  { name: "예측 모델 재학습", status: "running", last: "오늘 07:30", count: "진행중", next: "-" },
  { name: "리포트 집계", status: "pending", last: "어제 23:00", count: "대기중", next: "오늘 23:00" },
];

const MODEL_ACCURACY = [
  { month: "10월", mae: 2.41, rmse: 3.12 },
  { month: "11월", mae: 2.28, rmse: 2.97 },
  { month: "12월", mae: 2.15, rmse: 2.81 },
  { month: "1월", mae: 2.03, rmse: 2.65 },
  { month: "2월", mae: 1.94, rmse: 2.54 },
  { month: "3월", mae: 1.87, rmse: 2.43 },
];

const USERS = [
  { name: "김영호", email: "ykim@guncorp.co.kr", plan: "프리미엄", joined: "2025.12.08", last: "오늘", queries: 342 },
  { name: "박수연", email: "sypark@daewoo.co.kr", plan: "스탠다드", joined: "2026.01.15", last: "어제", queries: 128 },
  { name: "이재원", email: "jwlee@hanshin.com", plan: "프리미엄", joined: "2025.11.20", last: "오늘", queries: 489 },
  { name: "최민준", email: "mjchoi@hyundai-eng.com", plan: "무료", joined: "2026.02.10", last: "3일 전", queries: 24 },
  { name: "정다혜", email: "dhjeong@posco.co.kr", plan: "스탠다드", joined: "2026.01.28", last: "오늘", queries: 216 },
];

const DOT_COLORS: Record<string, string> = {
  success: "bg-emerald-500",
  running: "bg-amber-500",
  pending: "bg-red-500",
};

const PLAN_COLORS: Record<string, string> = {
  "프리미엄": "bg-blue-50 text-primary",
  "스탠다드": "bg-green-50 text-green-600",
  "무료": "bg-amber-50 text-amber-600",
};

export default function AdminPage() {
  return (
    <div>
      <div className="mb-5">
        <h1 className="text-xl font-extrabold">관리자 모니터링</h1>
        <p className="text-[13px] text-slate-500 mt-1">
          데이터 파이프라인 상태 · 예측 모델 성능 · 사용자 관리
        </p>
      </div>

      {/* KPI */}
      <div className="grid grid-cols-4 gap-4 mb-4">
        {KPI_DATA.map((k, i) => (
          <div key={i} className="bg-white rounded-[10px] p-[18px_20px] shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
            <div className="text-xs text-slate-500 font-medium mb-1.5">{k.label}</div>
            <div className="text-2xl font-extrabold">{k.value}</div>
            <div className="text-xs mt-1 text-green-600">{k.change}</div>
          </div>
        ))}
      </div>

      {/* 파이프라인 + 모델 성능 */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* 파이프라인 */}
        <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold">데이터 파이프라인 현황</div>
              <div className="text-xs text-slate-500 mt-0.5">실시간 배치 상태</div>
            </div>
            <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-green-50 text-green-600">
              ● 정상 운영
            </span>
          </div>
          {PIPELINES.map((p, i) => (
            <div key={i} className="flex items-center gap-3 py-2.5 border-b border-border last:border-b-0">
              <span className={`inline-block w-[7px] h-[7px] rounded-full ${DOT_COLORS[p.status]}`} />
              <div className="flex-1">
                <div className="text-[13px] font-semibold">{p.name}</div>
                <div className="text-[11.5px] text-slate-500">마지막 실행: {p.last} · {p.count}</div>
              </div>
              <div className="text-right text-[11.5px] text-slate-500">
                다음 실행<br />{p.next}
              </div>
            </div>
          ))}
        </div>

        {/* 모델 성능 */}
        <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
          <div className="flex items-center justify-between mb-4">
            <div>
              <div className="text-sm font-bold">예측 모델 성능 추이</div>
              <div className="text-xs text-slate-500 mt-0.5">MAE / RMSE 월별 변화</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={MODEL_ACCURACY} margin={{ top: 0, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="month" tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
              <YAxis domain={[1.5, 3.5]} tick={{ fontSize: 11, fill: "#94A3B8" }} axisLine={false} tickLine={false} />
              <Tooltip />
              <Line type="monotone" dataKey="mae" stroke="#0066CC" strokeWidth={2.5} dot={{ r: 4 }} name="MAE" />
              <Line type="monotone" dataKey="rmse" stroke="#DC2626" strokeWidth={2} strokeDasharray="5 3" dot={{ r: 3 }} name="RMSE" />
              <Legend iconType="circle" iconSize={8} />
            </LineChart>
          </ResponsiveContainer>
          <div className="grid grid-cols-2 gap-2 mt-3">
            <div className="p-3.5 bg-[#F8FAFC] rounded-lg text-center">
              <div className="text-[11px] text-slate-500 font-medium">현재 MAE</div>
              <div className="text-xl font-extrabold text-primary my-1">1.87</div>
              <div className="text-[11px] text-slate-500">% (사정률 기준)</div>
            </div>
            <div className="p-3.5 bg-[#F8FAFC] rounded-lg text-center">
              <div className="text-[11px] text-slate-500 font-medium">현재 RMSE</div>
              <div className="text-xl font-extrabold text-red-600 my-1">2.43</div>
              <div className="text-[11px] text-slate-500">% (사정률 기준)</div>
            </div>
          </div>
        </div>
      </div>

      {/* 사용자 테이블 */}
      <div className="bg-white rounded-[10px] p-5 shadow-[0_1px_4px_rgba(0,0,0,0.06),0_0_0_1px_rgba(0,0,0,0.04)]">
        <div className="flex items-center justify-between mb-4">
          <div className="text-sm font-bold">최근 가입 사용자</div>
          <button className="inline-flex items-center gap-1.5 px-3.5 py-[7px] rounded-[7px] text-[12.5px] font-semibold border-[1.5px] border-border hover:bg-[#F0F4F8] transition">
            전체 사용자 관리
          </button>
        </div>
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">이름</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">이메일</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">플랜</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">가입일</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">마지막 접속</th>
              <th className="text-left p-[10px_12px] text-[11.5px] font-semibold text-slate-500 border-b-[1.5px] border-border bg-[#F8FAFC]">조회 횟수</th>
            </tr>
          </thead>
          <tbody>
            {USERS.map((u, i) => (
              <tr key={i} className="hover:bg-[#F8FAFC]">
                <td className="p-[11px_12px] border-b border-border font-semibold">{u.name}</td>
                <td className="p-[11px_12px] border-b border-border text-[12.5px] text-slate-500">{u.email}</td>
                <td className="p-[11px_12px] border-b border-border">
                  <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full ${PLAN_COLORS[u.plan]}`}>
                    {u.plan}
                  </span>
                </td>
                <td className="p-[11px_12px] border-b border-border text-[12.5px] text-slate-500">{u.joined}</td>
                <td className="p-[11px_12px] border-b border-border text-[12.5px]">{u.last}</td>
                <td className="p-[11px_12px] border-b border-border font-bold">{u.queries}회</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
