# Synology DDNS + Let's Encrypt + 역방향 프록시 가이드

목적: **Synology 무료 도메인** (예: `bid-insight.synology.me`) 으로
HTTPS 외부 접속을 구성. 별도 도메인 구매·Cloudflare 계정 불필요.

대상 환경: DSM 7.x (Container Manager 설치됨)
예상 소요 시간: **약 30분**

---

## 0. 사전 점검

### 0-1. 공인 IP 보유 확인 (가장 중요)
가정용/사무실 인터넷이 **공인 IP**를 가지고 있어야 외부에서 접속 가능합니다.

**확인 방법:**
1. NAS 또는 PC에서 https://www.whatismyip.com 접속
2. 거기서 보이는 IP와, 공유기 WAN IP가 **같으면 공인 IP** ✅
3. 다르면 **NAT/CGNAT** → ISP에 공인 IP 신청 필요 (보통 무료, 또는 월 3천원)

KT/SK/LGU+ 가정용은 대부분 공인 IP. 일부 알뜰형/모바일 라우터는 NAT.

### 0-2. 공유기 관리자 접근
- 공유기 IP (보통 192.168.0.1 / 192.168.1.1) 와 관리자 비밀번호
- 포트포워딩 메뉴 사용 가능해야 함

### 0-3. 결정해야 할 사항
- [ ] 사용할 호스트 이름 (예: `bid-insight`, `myco-bid`, ...)
- [ ] 운영 환경 (Synology DDNS 도메인 결정)

---

## 1. Synology DDNS 호스트 등록

### 1-1. DSM 로그인 → DDNS 설정
1. **제어판 → 외부 액세스 → DDNS 탭**
2. **추가** 클릭
3. 입력:
   - **서비스 공급업체**: `Synology`
   - **호스트 이름**: 원하는 이름 입력 (예: `bid-insight`)
   - 자동으로 `.synology.me` 가 붙음 → `bid-insight.synology.me`
   - **이메일**: Synology 계정 이메일 입력
   - **외부 주소(IPv4)**: 자동 감지됨
   - **Heartbeat 설정**: 사용
   - **Let's Encrypt 인증서 받기**: ✅ **반드시 체크**
4. **확인** 클릭 → 약 30~60초 대기

### 1-2. 등록 확인
- DDNS 목록에 `bid-insight.synology.me` / 상태: **정상** 표시
- **제어판 → 보안 → 인증서**에 자동 발급된 Let's Encrypt 인증서 확인

---

## 2. 공유기 포트포워딩

### 2-1. 공유기 관리자 페이지 진입
- 192.168.0.1 (또는 ISP 제공 게이트웨이)
- 관리자 계정 로그인

### 2-2. 포트포워딩 등록 (NAS의 IP로)
**일반적 위치**: 「고급 설정 → NAT/포트포워딩」 또는 「외부 접속 설정」

| 외부 포트 | 내부 IP (NAS) | 내부 포트 | 프로토콜 | 용도 |
|---------|--------------|---------|--------|-----|
| 80 | 192.168.x.x | 80 | TCP | Let's Encrypt 인증서 갱신 |
| 443 | 192.168.x.x | 443 | TCP | HTTPS 서비스 |

⚠️ **주의:** DSM 관리포트(5000/5001)는 **절대 외부 노출 금지**.

### 2-3. UPnP 자동 포트포워딩 (선택)
DSM **제어판 → 외부 액세스 → 라우터 구성** 에서 UPnP로 자동 등록 가능.

---

## 3. DSM 역방향 프록시 설정

> Docker 컨테이너의 8000번을 외부 443/HTTPS로 매핑.

### 3-1. 응용프로그램 포털 진입
**제어판 → 로그인 포털 → 고급 → 역방향 프록시**
(DSM 7.2 이상은 **응용프로그램 포털 → 역방향 프록시**)

### 3-2. 만들기 → 새 규칙
**일반 탭:**
| 항목 | 값 |
|------|---|
| 설명 | `Bid Insight` |
| 출처 - 프로토콜 | **HTTPS** |
| 출처 - 호스트 이름 | `bid-insight.synology.me` |
| 출처 - 포트 | `443` |
| 출처 - HTTP/2 활성화 | ✅ |
| 출처 - HSTS 활성화 | ✅ (선택, 권장) |
| 대상 - 프로토콜 | **HTTP** |
| 대상 - 호스트 이름 | `localhost` |
| 대상 - 포트 | `8000` |

**사용자 정의 헤더 탭** (선택, WebSocket 대비 권장):
| 헤더 이름 | 값 |
|---------|---|
| `Upgrade` | `$http_upgrade` |
| `Connection` | `$connection_upgrade` |
| `X-Real-IP` | `$remote_addr` |
| `X-Forwarded-For` | `$proxy_add_x_forwarded_for` |
| `X-Forwarded-Proto` | `$scheme` |

→ **저장**

### 3-3. SSL 인증서 자동 매핑 확인
**제어판 → 보안 → 인증서 → 설정**:
- `bid-insight.synology.me` 가 Let's Encrypt 인증서를 사용하는지 확인.
- 자동 매핑되지 않았으면 드롭다운에서 수동 선택 후 **저장**.

---

## 4. Bid Insight 컨테이너 외부 노출 활성화

### 4-1. 운영 환경변수 (.env)
```env
APP_ENV=production
SECRET_KEY=<openssl rand -hex 32 결과>
CORS_ORIGINS=https://bid-insight.synology.me
G2B_API_KEY=El9lO0kHnF1ECVb6JjN8j...
SYNC_ENABLED=true
LOG_LEVEL=INFO
LOG_FILE=/app/data/server.log
WORKERS=2
```

### 4-2. docker-compose.prod.yml 포트 노출
파일에서 `ports:` 섹션 확인:
```yaml
ports:
  - "8000:8000"   # 127.0.0.1: 제거 → NAS 내부 네트워크 전체에서 접근 가능
```

(이미 본 가이드 발행 시점 기본값이 `0.0.0.0:8000:8000` 으로 설정되어 있음 — Cloudflare Tunnel 사용 시 `127.0.0.1:8000:8000` 으로 변경)

### 4-3. 재시작
```bash
cd /volume1/docker/bid-insight
docker compose -f docker-compose.prod.yml up -d
docker logs bid-backend | tail -10
```

---

## 5. 동작 검증

### 5-1. 내부망 검증
```bash
# NAS 자체에서
curl http://localhost:8000/healthz
# → {"status":"ok",...}
```

### 5-2. 외부망 검증 (스마트폰 LTE/5G로 권장)
```
https://bid-insight.synology.me/healthz
```
브라우저에서 접속:
- 자물쇠 🔒 표시 + Let's Encrypt 인증서
- JSON 응답 표시

### 5-3. 메인 페이지
```
https://bid-insight.synology.me
```
→ 로그인 화면 표시

---

## 6. 주의사항

### 6-1. 공인 IP 변경 시
- 가정용 인터넷은 IP가 가끔 바뀜
- DDNS는 자동으로 새 IP를 반영 (DSM의 Heartbeat 기능)
- 단, Let's Encrypt 갱신 시 80번 포트 정상 포워딩 필수

### 6-2. 인증서 갱신 실패 시
- DSM **로그 센터 → 보안** 에서 갱신 실패 메시지 확인
- 가장 흔한 원인: 80번 포트 포워딩 끊김 → 공유기 점검

### 6-3. CORS 동시 운영
NAS DDNS와 자체 도메인을 동시 운영하려면:
```env
CORS_ORIGINS=https://bid-insight.synology.me,https://bid.example.com
```

### 6-4. Synology 계정 의존
DDNS는 Synology 계정에 종속됨. 계정 삭제/만료 시 DDNS도 사용 불가.
**계정 비밀번호 + 복구 이메일 안전 관리 필수.**

---

## 7. 보안 강화 (권장)

### 7-1. 관리포트 외부 차단
**제어판 → 보안 → 방화벽**:
- 5000/5001 포트는 LAN(192.168.x.x)만 허용
- 외부에서 DSM 관리 차단

### 7-2. 2단계 인증
**제어판 → 사용자 → admin → 2단계 인증** 활성화

### 7-3. fail2ban / 자동 차단
**제어판 → 보안 → 자동 차단**:
- 10분 내 5회 실패 시 30일 차단

### 7-4. SSH는 평소 비활성
필요 시에만 임시로 활성화 (제어판 → 터미널 및 SNMP)

---

## 8. 문제 해결

| 증상 | 원인 / 해결 |
|------|----------|
| `502 Bad Gateway` | bid-backend 컨테이너 다운. `docker ps` 확인 |
| `526 Invalid SSL certificate` | 역방향 프록시 대상이 HTTP인데 HTTPS로 설정됨 |
| 외부 접속 안 됨 (내부는 OK) | 포트포워딩 누락 또는 ISP NAT — 공인 IP 확인 |
| 인증서 만료 알림 | 80번 포트포워딩 점검, DSM 인증서 메뉴에서 수동 갱신 |
| `Mixed Content` 경고 | 프론트엔드가 `http://` URL 사용 → 코드에서 상대경로 또는 `https://`로 |
| DDNS 호스트가 `오류` 상태 | Synology 계정 만료 또는 ISP IP 차단. DSM에서 재등록 |

---

## 9. 운영 체크리스트

매주:
- [ ] DDNS 상태 = `정상` (DSM 외부 액세스)
- [ ] Let's Encrypt 만료 30일 이상 남음
- [ ] `https://...synology.me/healthz` 정상 응답

매월:
- [ ] Synology 계정 로그인 (계정 활성 유지)
- [ ] 공유기 포트포워딩 규칙 그대로인지 확인 (펌웨어 업데이트 후 초기화 가능)

---

## 10. 향후 자체 도메인 추가 시

NAS DDNS는 그대로 두고 자체 도메인을 추가하는 흐름:

1. 자체 도메인 구매 (예: `example.com`)
2. 도메인 → NAS 공인 IP로 A 레코드 등록
3. DSM 역방향 프록시 규칙 추가 (`bid.example.com → localhost:8000`)
4. Let's Encrypt 인증서 추가 발급
5. `.env` 의 `CORS_ORIGINS` 에 도메인 추가:
   ```env
   CORS_ORIGINS=https://bid-insight.synology.me,https://bid.example.com
   ```
6. 백엔드 재시작

→ 두 도메인 모두 동시 운영 가능.

---

작성일: 2026-04-27
참고: https://kb.synology.com/ko-kr/DSM/help/DSM/AdminCenter/connection_ddns
