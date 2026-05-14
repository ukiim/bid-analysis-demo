/**
 * KBID 실 사이트 공개 페이지 수집 + 디자인 토큰 추출
 *
 * 결과:
 * - docs/kbid_reference/page_*.html  — 풀 HTML
 * - docs/kbid_reference/page_*.png   — 풀페이지 스크린샷
 * - docs/kbid_reference/tokens.json  — 추출한 색·여백·폰트
 */
import { chromium } from "playwright";
import path from "path";
import fs from "fs";

const OUT_DIR =
  "/Users/test/Desktop/SI/meet/공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발/.claude/worktrees/laughing-jennings-09ea6a/docs/kbid_reference";
fs.mkdirSync(OUT_DIR, { recursive: true });

const PAGES = [
  { url: "https://www.kbid.co.kr/", name: "00_home" },
  { url: "https://www.kbid.co.kr/ratio/index.htm", name: "01_ratio_main" },
  // 추가 공개 페이지가 발견되면 여기에 추가
];

(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1440, height: 900 },
    userAgent:
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
  });
  const page = await ctx.newPage();

  const tokensOut = {};
  for (const p of PAGES) {
    console.log(`Capturing ${p.name} ← ${p.url}`);
    try {
      await page.goto(p.url, { waitUntil: "networkidle", timeout: 30000 });
      await page.waitForTimeout(2000);
    } catch (e) {
      console.warn(`  [warn] ${p.url} navigation: ${e.message}`);
    }
    // Full HTML
    const html = await page.content();
    fs.writeFileSync(path.join(OUT_DIR, `${p.name}.html`), html, "utf8");
    // Screenshot
    try {
      await page.screenshot({
        path: path.join(OUT_DIR, `${p.name}.png`),
        fullPage: true,
      });
    } catch (e) {
      console.warn(`  [warn] screenshot: ${e.message}`);
    }
    // Token extraction — common KBID elements
    const tokens = await page.evaluate(() => {
      const pick = (el, props) => {
        const cs = getComputedStyle(el);
        const out = {};
        for (const k of props) out[k] = cs.getPropertyValue(k);
        return out;
      };
      const result = {};
      result.body = pick(document.body, [
        "background-color",
        "color",
        "font-family",
        "font-size",
        "line-height",
      ]);
      // header-like elements (top of page)
      const header =
        document.querySelector("header") ||
        document.querySelector(".header") ||
        document.querySelector("#header") ||
        document.querySelector("nav");
      if (header)
        result.header = pick(header, [
          "background-color",
          "color",
          "border-bottom",
          "height",
        ]);
      // form-table-like cells
      const formCells = Array.from(document.querySelectorAll("table th, table td"));
      result.formCells = formCells.slice(0, 8).map((el) =>
        pick(el, [
          "background-color",
          "color",
          "border",
          "border-color",
          "padding",
          "font-size",
        ])
      );
      // Buttons
      const buttons = Array.from(document.querySelectorAll("button, .btn, a.btn, input[type=button]"));
      result.buttons = buttons.slice(0, 8).map((el) =>
        pick(el, [
          "background-color",
          "background",
          "color",
          "border",
          "padding",
          "font-size",
          "font-weight",
        ])
      );
      // Links
      const links = Array.from(document.querySelectorAll("a")).slice(0, 8);
      result.links = links.map((el) =>
        pick(el, ["color", "text-decoration", "font-weight"])
      );
      return result;
    });
    tokensOut[p.name] = tokens;
    console.log(`  ✓ ${p.name}.html + .png`);
  }

  fs.writeFileSync(
    path.join(OUT_DIR, "tokens.json"),
    JSON.stringify(tokensOut, null, 2),
    "utf8"
  );
  console.log("Done.");
  await browser.close();
})();
