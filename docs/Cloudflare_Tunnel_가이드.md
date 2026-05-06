# Cloudflare Tunnel 설정 가이드 — 비드스타

목적: NAS의 8000번 포트를 인터넷에 직접 노출하지 않고도, **HTTPS 도메인으로 외부 접속** 가능하게 하기.
포트포워딩 / 공인 IP / Let's Encrypt 인증서 없이 동작합니다.

---

## ✨ 왜 Cloudflare Tunnel인가?

| 비교 | 포트포워딩 + Let's Encrypt | **Cloudflare Tunnel** |
|------|--------------------------|----------------------|
| 공인 IP 필요 | ✅ | ❌ |
| 공유기 포트포워딩 | ✅ | ❌ |
| SSL 인증서 발급/갱신 | 직접 관리 | 자동 |
| DDoS 방어 | ❌ | ✅ |
| 비용 | 무료 (단, 도메인 별도) | 무료 (단, 도메인 별도) |
| 설정 난이도 | 중상 | 중 |

---

## 0. 사전 준비

- [ ] Cloudflare 계정 (https://dash.cloudflare.com)
- [ ] **도메인이 Cloudflare에 등록되어 있어야 함**
  - 도메인 구매 후 네임서버를 Cloudflare로 변경 (보통 24시간 내 반영)
- [ ] NAS 측 컨테이너가 정상 실행 중 (`docker ps | grep bid-backend`)

---

## 1. Cloudflare Zero Trust 활성화

1. https://one.dash.cloudflare.com 접속
2. 좌측 **Access → Tunnels** 메뉴
3. 처음이라면 **"Sign up for Zero Trust"** 무료 플랜 선택
4. 팀 이름 설정 (예: `bid-insight`)

---

## 2. Tunnel 생성

1. **Networks → Tunnels → Create a tunnel** 클릭
2. **Cloudflared** 선택 → "Next"
3. Tunnel 이름: `bid-insight-nas` → "Save tunnel"
4. **Install connector** 화면에서 **Docker** 탭 선택
5. 표시된 명령 복사 (이런 형태):
   ```bash
   docker run cloudflare/cloudflared:latest tunnel --no-autoupdate run --token <긴_토큰_문자열>
   ```
6. **토큰 부분만 복사** 해서 다음 단계에서 사용

---

## 3. NAS에 Cloudflared 컨테이너 추가

`docker-compose.prod.yml`에 cloudflared 서비스를 추가:

```yaml
services:
  backend:
    # ... 기존 설정 그대로 ...

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: bid-cloudflared
    restart: unless-stopped
    command: tunnel --no-autoupdate run --token ${CLOUDFLARE_TUNNEL_TOKEN}
    depends_on:
      backend:
        condition: service_healthy
```

`.env` 에 토큰 추가:
```env
CLOUDFLARE_TUNNEL_TOKEN=eyJhI...토큰_전체_문자열
```

재시작:
```bash
docker compose -f docker-compose.prod.yml up -d
docker logs bid-cloudflared | tail -20
# "Connection registered" 메시지 확인
```

---

## 4. Public Hostname 등록 (도메인 연결)

Cloudflare Zero Trust → 방금 만든 Tunnel 클릭 → **Public Hostname** 탭:

1. **Add a public hostname** 클릭
2. 입력:
   - Subdomain: `bid` (또는 원하는 서브도메인)
   - Domain: `example.com` (자신의 도메인)
   - Path: 비움
   - Service Type: `HTTP`
   - URL: `backend:8000` (Docker 네트워크 내부 호스트명)
3. **Save hostname**

→ 약 1~2분 후 https://bid.example.com 접속 시 서비스가 응답합니다.

---

## 5. SSL/TLS 모드 확인

Cloudflare Dashboard → 해당 도메인 선택 → **SSL/TLS → Overview**:
- **Full** 또는 **Flexible** 으로 설정 (Tunnel 사용 시 둘 다 정상 동작)
- **Full (strict)** 는 origin 인증서 필요 → Tunnel 환경에서는 권장 안 함

---

## 6. 접근 제어 (선택사항 — 추천)

내부망 전용 운영이라면 Cloudflare Access로 보호 가능:

1. Zero Trust → **Access → Applications → Add an application**
2. **Self-hosted** 선택
3. 도메인: `bid.example.com`
4. **Policy 추가** → "이메일이 admin@example.com 인 사용자만 허용" 등
5. 저장

→ 외부에서 접속 시 Cloudflare 로그인 화면이 먼저 뜨고, 인증 통과 시 우리 서비스로 진입.

---

## 7. CORS_ORIGINS 업데이트

`.env` 수정 후 백엔드 재시작:
```env
CORS_ORIGINS=https://bid.example.com
```
```bash
docker compose -f docker-compose.prod.yml up -d backend
```

---

## 8. 동작 검증

```bash
# 외부에서 (스마트폰 4G 등으로)
curl https://bid.example.com/healthz
# {"status":"ok","checks":{"db":"ok","scheduler":"running","env":"production"}}

curl https://bid.example.com/api/v1/meta/regions
# ["서울","경기",...]
```

브라우저: https://bid.example.com → 로그인 화면

---

## 9. 문제 해결

| 증상 | 진단 / 해결 |
|------|-----------|
| `502 Bad Gateway` | cloudflared가 backend를 못 찾음. compose 같은 네트워크인지 확인. URL을 `backend:8000` 으로 (호스트명 정확히) |
| `Tunnel is offline` | `docker logs bid-cloudflared` 토큰 오류 또는 인터넷 연결 확인 |
| `522 Connection timed out` | backend 컨테이너가 다운. `docker ps` 확인 |
| 도메인이 적용 안 됨 | DNS 전파 대기 (최대 5분). `dig bid.example.com` 으로 CNAME 확인 |
| Mixed Content 경고 | 프론트엔드에서 절대 URL이 `http://` 인지 확인 → `https://`로 변경 또는 상대 경로 사용 |

---

## 10. 비용 / 한도

- **무료 플랜 한도**: 월 50명까지 Access Application 사용자, Tunnel 자체는 무제한
- 트래픽 비용: **무료** (Cloudflare 측에서 부담)
- 도메인 비용: 별도 (.com 기준 연 1.5만원)

---

## 11. 운영 시 추천 설정

### 11-1. 자동 재시작 (cloudflared 죽음 방지)
이미 `restart: unless-stopped` 로 설정됨.

### 11-2. 다중 NAS 페일오버
같은 Tunnel을 여러 NAS에서 동시에 실행하면 자동으로 로드밸런싱 + 페일오버 됩니다.

### 11-3. 모니터링
Zero Trust → Tunnels → 해당 Tunnel 클릭 → **Metrics** 탭에서 실시간 트래픽 / 응답시간 확인.

---

## 12. 대안: NAS 자체 리버스 프록시 사용

Cloudflare Tunnel을 사용하지 않고 NAS의 응용프로그램 포털 + Let's Encrypt를 쓰는 방법:

1. DSM **제어판 → 외부 액세스 → DDNS** 설정
2. **응용프로그램 포털 → 역방향 프록시**:
   - 출처: `bid.example.com:443`
   - 대상: `localhost:8000`
3. **제어판 → 보안 → 인증서**: Let's Encrypt 신청
4. 공유기 포트포워딩 80/443 → NAS

→ 단점: 공인 IP 필요, DDoS 방어 없음, 인증서 갱신 직접 관리.

---

작성일: 2026-04-27
참고: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
