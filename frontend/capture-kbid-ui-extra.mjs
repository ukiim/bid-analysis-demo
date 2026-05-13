// 확장 캡쳐 — 향후 기능 추가 고려 (모바일/태블릿 반응형, 풍부한 데이터, 에러/빈 상태)
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const OUT_DIR = "/Users/test/Desktop/SI/meet/공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발/docs/kbid_ui_screenshots";
fs.mkdirSync(OUT_DIR, { recursive: true });

const TOKEN =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiI0ZmE5NDcxZC1iMDM3LTRjYjMtOTFiZS1jYmYzODI5M2I1NjgiLCJleHAiOjE3Nzg3MTg2NTB9.dIO0oUo_3tdOMMqWnRbXYoJHplDNDfO98EIZdnaSdQk";
const BASE = "http://localhost:3100";
const SPARSE_ID = "abfebe63-4f7e-4f76-9a98-097d0e58e5e3"; // 1건
const RICH_ID = "2da0a2d8-b8db-4ce6-938d-dab3818be871"; // 1,904건

async function clickSidebar(page, label) {
  const btn = page.locator(`aside button:has-text("${label}")`).first();
  await btn.click();
  await page.waitForTimeout(2000);
}

(async () => {
  const browser = await chromium.launch();

  // === 1. 풍부한 데이터 분석 페이지 (1,904건) ===
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => localStorage.setItem("token", t), TOKEN);

    const rich = [
      { url: `${BASE}/analysis/${RICH_ID}?tab=tab3`, name: "11_analysis_rich_tab3.png" },
      { url: `${BASE}/analysis/${RICH_ID}?tab=tab1`, name: "12_analysis_rich_tab1_chart.png" },
      { url: `${BASE}/analysis/${RICH_ID}?tab=tab2`, name: "13_analysis_rich_tab2_preliminary.png" },
      { url: `${BASE}/analysis/${RICH_ID}?tab=tab4`, name: "14_analysis_rich_tab4_table.png" },
    ];
    for (const s of rich) {
      console.log(`Capturing ${s.name} ...`);
      await page.goto(s.url, { waitUntil: "networkidle", timeout: 60000 });
      await page.waitForTimeout(3000);
      await page.screenshot({ path: path.join(OUT_DIR, s.name), fullPage: true });
    }
    await ctx.close();
  }

  // === 2. 모바일 (375x812) — 5개 화면 ===
  {
    const ctx = await browser.newContext({
      viewport: { width: 375, height: 812 },
      deviceScaleFactor: 2,
    });
    const page = await ctx.newPage();
    await page.addInitScript((t) => localStorage.setItem("token", t), TOKEN);

    console.log("Capturing 15_mobile_announcements.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(OUT_DIR, "15_mobile_announcements.png"), fullPage: true });

    console.log("Capturing 16_mobile_analysis.png ...");
    await page.goto(`${BASE}/analysis/${SPARSE_ID}`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, "16_mobile_analysis.png"), fullPage: true });

    console.log("Capturing 17_mobile_prediction.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await clickSidebar(page, "사정률 예측");
    await page.screenshot({ path: path.join(OUT_DIR, "17_mobile_prediction.png"), fullPage: true });

    console.log("Capturing 18_mobile_statistics.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await clickSidebar(page, "통계 리포트");
    await page.screenshot({ path: path.join(OUT_DIR, "18_mobile_statistics.png"), fullPage: true });

    console.log("Capturing 19_mobile_admin.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await clickSidebar(page, "관리자 모니터링");
    await page.screenshot({ path: path.join(OUT_DIR, "19_mobile_admin.png"), fullPage: true });

    await ctx.close();
  }

  // === 3. 태블릿 (768x1024) — 메인 페이지 ===
  {
    const ctx = await browser.newContext({ viewport: { width: 768, height: 1024 } });
    const page = await ctx.newPage();
    await page.addInitScript((t) => localStorage.setItem("token", t), TOKEN);

    console.log("Capturing 20_tablet_announcements.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2000);
    await page.screenshot({ path: path.join(OUT_DIR, "20_tablet_announcements.png"), fullPage: true });

    console.log("Capturing 21_tablet_analysis.png ...");
    await page.goto(`${BASE}/analysis/${SPARSE_ID}`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, "21_tablet_analysis.png"), fullPage: true });

    await ctx.close();
  }

  // === 4. 빈/에러 상태 (no auth, invalid ID) ===
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
    const page = await ctx.newPage();
    // No token injected = no auth

    console.log("Capturing 22_no_auth_announcements.png ...");
    await page.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, "22_no_auth_announcements.png"), fullPage: true });

    console.log("Capturing 23_no_auth_analysis.png ...");
    await page.goto(`${BASE}/analysis/${SPARSE_ID}`, { waitUntil: "networkidle", timeout: 30000 });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, "23_no_auth_analysis.png"), fullPage: true });

    // Invalid ID with auth
    await page.addInitScript((t) => localStorage.setItem("token", t), TOKEN);
    console.log("Capturing 24_invalid_analysis_id.png ...");
    await page.goto(`${BASE}/analysis/00000000-0000-0000-0000-000000000000`, {
      waitUntil: "networkidle",
      timeout: 30000,
    });
    await page.waitForTimeout(2500);
    await page.screenshot({ path: path.join(OUT_DIR, "24_invalid_analysis_id.png"), fullPage: true });

    await ctx.close();
  }

  await browser.close();
  console.log("Done.");
})();
