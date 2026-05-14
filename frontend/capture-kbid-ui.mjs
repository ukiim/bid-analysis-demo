import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const OUT_DIR = "/Users/test/Desktop/SI/meet/공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발/docs/kbid_ui_screenshots";
fs.mkdirSync(OUT_DIR, { recursive: true });

const BASE = "http://localhost:3100";
const ID = "aabbcca3-8351-4fa1-9a2b-d6cb3cf8a564";  // 워크트리 DB (3000건) 의 유효 ID

// admin@bidinsight.kr 토큰 (만료 ~2026-05+1년)
const REAL_TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI4YTY3NGIxMS00YmI2LTQzMTUtYTM0My02YTIyYjNmMDAxNjEiLCJleHAiOjE3Nzg3NzU0ODR9.jGhdoW9fJRC5E_KUthTX2rh2RkT4Flbr7HApfZJVUzU";

async function captureSidebar(page, pageKey, fileName) {
  // v3: 사이드바 → TopNav. ?page= 쿼리로 진입
  await page.goto(`${BASE}/?page=${pageKey}`, { waitUntil: "networkidle", timeout: 30000 });
  await page.waitForTimeout(2500);
  const file = path.join(OUT_DIR, fileName);
  await page.screenshot({ path: file, fullPage: true });
  console.log(`  → ${file}`);
}

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  await page.addInitScript((token) => {
    window.localStorage.setItem("token", token);
  }, REAL_TOKEN);

  // v4: KBID 4-탭 + 2개 보조 모드 (sec-company-rates / sec-rate-table)
  const urlShots = [
    { url: `${BASE}/login`, name: "00_login_page.png" },
    { url: `${BASE}/`, name: "01_announcements_list.png" },
    { url: `${BASE}/analysis/${ID}`, name: "02_analysis_tab3_default.png" },
    { url: `${BASE}/analysis/${ID}?tab=tab1`, name: "03_analysis_tab1_rate_chart.png" },
    { url: `${BASE}/analysis/${ID}?tab=tab2`, name: "04_analysis_tab2_preliminary_freq.png" },
    { url: `${BASE}/analysis/${ID}?tab=sec-rate-table`, name: "05_analysis_tab4_rate_table.png" },
    { url: `${BASE}/analysis/${ID}?tab=tab3&rate=99.36`, name: "06_analysis_tab3_with_selected_rate.png" },
    { url: `${BASE}/analysis/${ID}?period_months=6&category=service`, name: "10_analysis_filters_applied.png" },
    // KBID 동등 4-탭 + 우측 보조 모드
    { url: `${BASE}/analysis/${ID}?tab=sec-company-rates`, name: "25_analysis_tab5_company_rates.png" },
    { url: `${BASE}/analysis/${ID}?tab=tab4`, name: "26_analysis_tab6_comprehensive.png" },
  ];

  for (const s of urlShots) {
    console.log(`Capturing ${s.name} ...`);
    await page.goto(s.url, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, s.name), fullPage: true });
    console.log(`  → ${path.join(OUT_DIR, s.name)}`);
  }

  // SPA pages — v3: ?page= 쿼리
  const sidebarShots = [
    { key: "prediction", name: "07_prediction_page.png" },
    { key: "statistics", name: "08_statistics_page.png" },
    { key: "admin", name: "09_admin_page.png" },
  ];

  for (const s of sidebarShots) {
    console.log(`Capturing ${s.name} via ?page=${s.key} ...`);
    await captureSidebar(page, s.key, s.name);
  }

  await browser.close();
  console.log("Done.");
})();
