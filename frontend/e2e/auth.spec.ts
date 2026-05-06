import { test, expect, request as apiRequest } from '@playwright/test';
import { TEST_USER, loginAsTestUser } from './_helpers';

test.describe('인증 + 사이드바 라우팅', () => {
  test('로그인 페이지 → 비드스타 브랜드 + 데모 빠른 로그인 노출', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('비드스타').first()).toBeVisible();
    await expect(page.getByText('데모 빠른 로그인')).toBeVisible();
  });

  test('데모 빠른 로그인 → 공고화면 진입', async ({ page }) => {
    await page.goto('/');
    await page.getByText('데모 빠른 로그인').click();
    await page.waitForURL(/\/(announcements|admin)/);
    // 사이드바 비드스타 + 공고화면 메뉴 보여야 함
    await expect(page.locator('.brand-name').first()).toContainText('비드스타');
  });

  test('서비스 사이드바 5개 메뉴 + 종합분석 빈 상태', async ({ page, request }) => {
    await loginAsTestUser(page, request);
    await page.goto('/announcements');
    await expect(page.getByTestId('nav-announcements')).toBeVisible();
    await expect(page.getByTestId('nav-comprehensive')).toBeVisible();
    await expect(page.getByTestId('nav-mypage')).toBeVisible();

    // 종합분석 클릭 → 공고 미선택 안내
    await page.getByTestId('nav-comprehensive').click();
    await expect(page.getByText('공고를 선택해주세요')).toBeVisible();
  });
});
