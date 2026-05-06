import { Page, expect, APIRequestContext } from '@playwright/test';

export const TEST_USER = {
  email: 'playwright_e2e@example.com',
  password: 'playwright1234',
  name: 'Playwright E2E',
};

// 토큰 캐시 — login rate-limit (10/min) 회피
let _cachedToken: string | null = null;
let _cachedAt = 0;
const CACHE_TTL_MS = 25 * 60 * 1000;  // 25분 (서버 토큰 만료보다 짧게)

/** 테스트 사용자 회원가입 (이미 존재하면 무시) + 로그인 → localStorage 토큰 주입 */
export async function loginAsTestUser(page: Page, request: APIRequestContext) {
  // 캐시 hit → register/login 호출 스킵 (rate limit 회피)
  if (_cachedToken && Date.now() - _cachedAt < CACHE_TTL_MS) {
    await page.goto('/');
    await page.evaluate(t => localStorage.setItem('token', t), _cachedToken);
    return _cachedToken;
  }
  // 1) 회원가입 시도 (실패해도 무시 — 이미 존재 가능)
  // 백엔드 register 는 query params 사용
  try {
    const qs = new URLSearchParams({
      username: TEST_USER.email,
      email: TEST_USER.email,
      password: TEST_USER.password,
      name: TEST_USER.name,
    }).toString();
    await request.post(`/api/v1/auth/register?${qs}`);
  } catch {}

  // 2) 로그인 → 토큰 획득
  const loginResp = await request.post(
    `/api/v1/auth/login?username=${encodeURIComponent(TEST_USER.email)}&password=${encodeURIComponent(TEST_USER.password)}`,
  );
  expect(loginResp.ok()).toBeTruthy();
  const { access_token } = await loginResp.json();

  // 캐시 저장
  _cachedToken = access_token;
  _cachedAt = Date.now();

  // 3) localStorage 에 주입 후 페이지 진입 (자동 인증)
  await page.goto('/');
  await page.evaluate(t => localStorage.setItem('token', t), access_token);
  return access_token;
}

/** 분석 가능한 공고 1건의 ID 가져오기 — fixture 가 없으면 backend DB에서 첫 G2B 공고 사용 */
export async function getAnalyzableAnnouncementId(request: APIRequestContext, token: string): Promise<string> {
  const resp = await request.get('/api/v1/announcements?limit=1', {
    headers: { Authorization: `Bearer ${token}` },
  });
  expect(resp.ok()).toBeTruthy();
  const data = await resp.json();
  const items = data.items || data;
  expect(items.length).toBeGreaterThan(0);
  return items[0].id;
}
