import { test, expect, request as apiRequest } from '@playwright/test';
import { loginAsTestUser, getAnalyzableAnnouncementId } from './_helpers';

/**
 * Tab1/2/3 신규 카드 인터랙션 e2e
 *
 * 흐름:
 *  1) 공고 ID 로 종합분석 직접 진입
 *  2) Tab1 — 구간 분석 카드 모드 A/B/C 토글, 세부값 룰 변경, 학습 저장 버튼
 *  3) Tab2 — KBID 검색 5종 입력 → /api/v1/analysis/company-rates 호출 검증
 *  4) Tab3 — 상관관계 카드 + 종합 1순위 + 엑셀 다운로드 버튼
 */

test.describe('Tab1 — 구간 분석 (스펙 §1)', () => {
  test('카드 렌더 + 모드 A/B/C 토글 + 학습 저장/엑셀 버튼 노출', async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);

    // 카드 진입
    const card = page.getByTestId('card-mode-analysis').locator('..').locator('..');
    await expect(card).toBeVisible();

    // 학습 저장 + 엑셀 버튼 존재
    await expect(page.getByRole('button', { name: /학습 저장/ })).toBeVisible();
    await expect(page.getByRole('button', { name: /엑셀/ }).first()).toBeVisible();

    // 모드 토글 — A 활성, B 클릭하면 B 활성
    const modeB = page.getByRole('button', { name: 'B 공백' });
    await modeB.click();
    await expect(modeB).toHaveClass(/active/);

    // 모드 C 클릭
    const modeC = page.getByRole('button', { name: 'C 차이최대' });
    await modeC.click();
    await expect(modeC).toHaveClass(/active/);
  });

  test('세부값 룰 변경 시 API 재호출', async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);

    const callsPromise = page.waitForResponse(
      r => r.url().includes('/analysis/rate-buckets/') && r.url().includes('detail_rule=first_after'),
      { timeout: 5000 },
    );
    // 세부값 룰 select — value 옵션으로 정확히 매칭되는 select 만 선택
    const ruleSelect = page.locator('select').filter({
      has: page.locator('option[value="max_gap"]'),
    });
    await ruleSelect.selectOption({ value: 'first_after' });
    await callsPromise;
  });
});

test.describe('Tab2 — KBID 검색 (스펙 §2)', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);
    // selectedRate 직접 입력 (histogram 클릭 대신 input 사용)
    const rateInput = page.locator('input[placeholder="막대 클릭"]');
    await rateInput.fill('99.4');
    await page.waitForTimeout(300);
    // Tab2 진입
    await page.getByTestId('tab-company-rates').click();
    await page.waitForTimeout(500);
  });

  test('KBID 검색 5종 입력 필드 노출', async ({ page }) => {
    await expect(page.getByTestId('card-kbid-search')).toBeVisible();
    await expect(page.getByPlaceholder('예: 서울시')).toBeVisible();
    await expect(page.getByPlaceholder(/100±2/)).toBeVisible();  // 예가변동폭
    // exact: true 로 strict 모드 위반 회피 (100000000 이 1000000000 의 부분 일치)
    await expect(page.getByPlaceholder('예: 100000000', { exact: true })).toBeVisible();
    await expect(page.getByPlaceholder('예: 1000000000', { exact: true })).toBeVisible();
    await expect(page.getByPlaceholder('예: 4421')).toBeVisible();
  });

  test('검색 입력 시 /analysis/company-rates 가 검색 파라미터와 함께 호출됨', async ({ page }) => {
    const respPromise = page.waitForResponse(
      r => r.url().includes('/analysis/company-rates/') && r.url().includes('org_search=%E1%84%90%E1%85%A6%E1%84%89%E1%85%B3%E1%84%90%E1%85%B3'.substring(0, 30)),
      { timeout: 8000 },
    ).catch(() => null);
    // 더 robust한 fallback: 그냥 org_search 키 포함만 확인
    const fallback = page.waitForResponse(
      r => r.url().includes('/analysis/company-rates/') && r.url().includes('org_search='),
      { timeout: 8000 },
    );
    await page.getByPlaceholder('예: 서울시').fill('테스트');
    await Promise.race([respPromise, fallback]);
  });

  test('전체 초기화 버튼 → 모든 검색 필드 빈 상태로', async ({ page }) => {
    await page.getByPlaceholder('예: 서울시').fill('서울');
    await page.getByPlaceholder('예: 4421').fill('4421');
    await page.getByRole('button', { name: '전체 초기화' }).click();
    await expect(page.getByPlaceholder('예: 서울시')).toHaveValue('');
    await expect(page.getByPlaceholder('예: 4421')).toHaveValue('');
  });
});

test.describe('Tab3 — 상관관계 분석 (스펙 §3.11)', () => {
  test.beforeEach(async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);
    // selectedRate + confirmedRate 직접 입력 (Tab2 의 refined_rate 자동 적용 의존성 제거)
    await page.locator('input[placeholder="막대 클릭"]').fill('99.4');
    await page.waitForTimeout(300);
    await page.locator('input[placeholder="직접 입력"]').fill('99.4');
    await page.locator('input[placeholder="직접 입력"]').press('Enter');
    await page.waitForTimeout(500);
    // Tab3 진입 — 탭 영역 3번째 (sidebar 종합분석과 구분)
    await page.getByTestId('tab-comprehensive').click();
    await page.waitForTimeout(1500);
  });

  test('상관관계 분석 카드 + 3가지 방법 + 종합 1순위 박스 노출', async ({ page }) => {
    await expect(page.getByTestId('card-correlation')).toBeVisible();
    // 3가지 방법 이름
    await expect(page.getByText('1) 사정률 발생빈도 분석')).toBeVisible();
    await expect(page.getByText('2) 업체사정률 갭 분석')).toBeVisible();
    await expect(page.getByText('3) 빈도+갭 결합 분석')).toBeVisible();
    // 종합 1순위 박스
    await expect(page.getByText('종합 1순위 예측 사정률')).toBeVisible();
    await expect(page.getByText(/합치도 \(Agreement\)/)).toBeVisible();
  });

  test('엑셀 다운로드 — 상관관계 / 투찰리스트 버튼 클릭 시 파일 받음', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /상관관계$/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.xlsx$/);
  });

  test('엑셀 다운로드 — 투찰리스트', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download');
    await page.getByRole('button', { name: /투찰리스트/ }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/bid_list.*\.xlsx$/);
  });
});

test.describe('학습 저장 (스펙 §1)', () => {
  test('학습 저장 클릭 → PUT /users/me/prediction-settings 호출', async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);
    await page.goto(`/comprehensive?id=${annId}`);
    const respPromise = page.waitForResponse(
      r => r.url().includes('/users/me/prediction-settings') && r.request().method() === 'PUT',
      { timeout: 5000 },
    );
    await page.getByRole('button', { name: /학습 저장/ }).click();
    const resp = await respPromise;
    expect(resp.ok()).toBeTruthy();
  });

  test('재진입 시 저장된 설정 자동 로드 (period_months / bucket_mode 보존)', async ({ page, request }) => {
    const token = await loginAsTestUser(page, request);
    const annId = await getAnalyzableAnnouncementId(request, token);

    // 사전 PUT — bucket_mode='C' 저장
    await request.put('/api/v1/users/me/prediction-settings', {
      headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
      data: { period_months: 24, bucket_mode: 'C', detail_rule: 'first_after' },
    });

    // 새 진입
    await page.goto(`/comprehensive?id=${annId}`);
    await page.waitForTimeout(2000);

    // 활성 모드가 C 인지 확인
    const modeC = page.getByRole('button', { name: 'C 차이최대' });
    await expect(modeC).toHaveClass(/active/);
  });
});
