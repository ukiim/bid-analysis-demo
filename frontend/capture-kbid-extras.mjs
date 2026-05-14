/**
 * KBID 추가 공개 페이지 수집 (Phase 1 v4)
 * 로그인 없이 접근 가능한 공개 페이지에서 디자인 토큰을 더 정확히 추출
 */
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const OUT_DIR =
  "/Users/test/Desktop/SI/meet/공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발/.claude/worktrees/laughing-jennings-09ea6a/docs/kbid_reference/v4";
fs.mkdirSync(OUT_DIR, { recursive: true });

// KBID 공개 가능한 페이지들 (분석 화면은 유료 회원 전용이라 제외)
const PAGES = [
  { url: "https://www.kbid.co.kr/", name: "v4_home" },
  { url: "https://www.kbid.co.kr/help/index.htm", name: "v4_help" },
  { url: "https://www.kbid.co.kr/policy/index.htm", name: "v4_policy" },
];

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });
  const page = await ctx.newPage();

  const tokens = {};
  for (const p of PAGES) {
    console.log(`Capturing ${p.name} ← ${p.url}`);
    try {
      await page.goto(p.url, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
    } catch (e) {
      console.warn(`  [warn] ${e.message}`);
      continue;
    }
    const html = await page.content();
    fs.writeFileSync(path.join(OUT_DIR, `${p.name}.html`), html, "utf8");
    try {
      await page.screenshot({ path: path.join(OUT_DIR, `${p.name}.png`), fullPage: true });
    } catch (e) {}
    // 추출
    const t = await page.evaluate(() => {
      const out = { tables: [], buttons: [], headerSize: null };
      const tables = document.querySelectorAll("table");
      for (const t of Array.from(tables).slice(0, 5)) {
        const cs = getComputedStyle(t);
        const th = t.querySelector("th");
        const td = t.querySelector("td");
        out.tables.push({
          width: cs.width,
          borderCollapse: cs.borderCollapse,
          th: th ? { bg: getComputedStyle(th).backgroundColor, p: getComputedStyle(th).padding, fs: getComputedStyle(th).fontSize } : null,
          td: td ? { p: getComputedStyle(td).padding, fs: getComputedStyle(td).fontSize, border: getComputedStyle(td).border } : null,
        });
      }
      const header = document.querySelector("#header") || document.querySelector("header") || document.querySelector("[class*=header]");
      if (header) {
        const r = header.getBoundingClientRect();
        out.headerSize = { width: r.width, height: r.height };
      }
      return out;
    });
    tokens[p.name] = t;
  }
  fs.writeFileSync(path.join(OUT_DIR, "tokens-v4.json"), JSON.stringify(tokens, null, 2));
  console.log("Done. Output:", OUT_DIR);
  await browser.close();
})();
