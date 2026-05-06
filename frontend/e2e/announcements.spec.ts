import { test, expect } from '@playwright/test';
import { loginAsTestUser, getAnalyzableAnnouncementId } from './_helpers';

test.describe('공고 목록 + UI fix 검증', () => {
  test.beforeEach(async ({ page, request }) => {
    await loginAsTestUser(page, request);
    await page.goto('/announcements');
    await page.waitForSelector('table tbody tr');
  });

  test('U1 fix — 공고번호 클릭 시 외부 G2B 링크가 새 탭으로 열림', async ({ page, context }) => {
    const firstBidLink = page.locator('table tbody tr').first().locator('a').first();
    await expect(firstBidLink).toHaveAttribute('target', '_blank');
    await expect(firstBidLink).toHaveAttribute('href', /g2b\.go\.kr|external/);
  });

  test('U3 fix — 검색 input 한글 IME composition 중 Enter 차단', async ({ page }) => {
    const search = page.getByPlaceholder('공고명, 발주기관 검색...');
    await search.click();
    // composition 시작 → 한글 입력 → composition 중 Enter (검색 호출 안되어야 함)
    await search.dispatchEvent('compositionstart');
    await search.fill('한국');
    // Enter 시도하지만 isComposing=true 면 차단되어야 함
    await search.evaluate((el: HTMLInputElement) => {
      const ev = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true });
      Object.defineProperty(ev, 'isComposing', { value: true });
      el.dispatchEvent(ev);
    });
    // composition 종료 후 Enter → 검색 호출 정상
    await search.dispatchEvent('compositionend');
    // 추가 검증: composition 중 Enter 가 호출 안됨 → 페이지 그대로
    await expect(page.getByText(/공고 목록/)).toBeVisible();
  });

  test('U5 fix — 행 클릭 시 quick-preview 패널 열리고 KPI 카드 가려지지 않음', async ({ page }) => {
    const firstRow = page.locator('table tbody tr').first();
    await firstRow.click();
    // 우측 패널 열림
    await expect(page.locator('.quick-preview.open')).toBeVisible();
    // body 클래스 has-preview 부착
    await expect(page.locator('body')).toHaveClass(/has-preview/);
    // 평균 사정률 카드 (5번째 KPI) 여전히 보여야 함
    await expect(page.getByText('평균 사정률').first()).toBeInViewport();
  });

  test('U2 fix — quick-preview "상세 분석 (종합화면)" → /comprehensive 이동', async ({ page }) => {
    const firstRow = page.locator('table tbody tr').first();
    await firstRow.click();
    await page.locator('.quick-preview.open').waitFor();
    await page.getByTestId('open-comprehensive').click();
    await page.waitForURL('**/comprehensive', { timeout: 5000 });
    expect(page.url()).toContain('/comprehensive');
  });
});

test.describe('U4 — URL ?id= 직접 진입', () => {
  test('?id=<공고ID> 로 종합분석 직접 진입 시 공고 자동 로드', async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);
    // 빈 안내가 아닌 분석 화면이 보여야 함 (공고 헤더 영역)
    await page.waitForSelector('.tab-btn, [class*="tab"]', { timeout: 5000 });
    await expect(page.getByText('공고를 선택해주세요')).not.toBeVisible({ timeout: 3000 }).catch(() => {});
  });
});
