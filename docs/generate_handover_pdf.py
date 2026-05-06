"""클라이언트 인수인계 체크리스트 PDF 생성 — Noto Sans KR"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.graphics.shapes import Drawing, Rect


# ── 폰트 ──────────────────────────────────────────────────────────
FONT_DIR = os.path.expanduser("~/Library/Fonts")
pdfmetrics.registerFont(TTFont('NotoSansKR', os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Bold', os.path.join(FONT_DIR, 'NotoSansKR-Bold.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Medium', os.path.join(FONT_DIR, 'NotoSansKR-Medium.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Light', os.path.join(FONT_DIR, 'NotoSansKR-Light.ttf')))
registerFontFamily('NotoSansKR', normal='NotoSansKR', bold='NotoSansKR-Bold')

FONT = 'NotoSansKR'
FONT_BOLD = 'NotoSansKR-Bold'
FONT_MEDIUM = 'NotoSansKR-Medium'
FONT_LIGHT = 'NotoSansKR-Light'

# ── 색상 ──────────────────────────────────────────────────────────
PRIMARY = HexColor('#0066CC')
PRIMARY_DARK = HexColor('#1A3353')
LIGHT_BG = HexColor('#F0F5FB')
BORDER = HexColor('#D0D7E3')
TEXT_PRIMARY = HexColor('#222831')
TEXT_SECONDARY = HexColor('#5A6A7E')
WHITE = white
SECTION_BG = HexColor('#F7F9FC')
ACCENT_GREEN = HexColor('#16A34A')
ACCENT_AMBER = HexColor('#F59E0B')
ACCENT_RED = HexColor('#DC2626')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "클라이언트_인수인계_체크리스트.pdf")

# ── 스타일 ────────────────────────────────────────────────────────
style_title = ParagraphStyle('Title', fontName=FONT_BOLD, fontSize=20, leading=26, textColor=WHITE, alignment=TA_LEFT)
style_subtitle = ParagraphStyle('Subtitle', fontName=FONT, fontSize=10, leading=14, textColor=HexColor('#B0C4DE'), alignment=TA_LEFT)
style_meta = ParagraphStyle('Meta', fontName=FONT_LIGHT, fontSize=9, leading=13, textColor=HexColor('#B0C4DE'), alignment=TA_RIGHT)
style_section = ParagraphStyle('Section', fontName=FONT_BOLD, fontSize=14, leading=19, textColor=PRIMARY_DARK, spaceBefore=14, spaceAfter=8)
style_subsection = ParagraphStyle('Subsection', fontName=FONT_BOLD, fontSize=11, leading=16, textColor=PRIMARY, spaceBefore=10, spaceAfter=5)
style_body = ParagraphStyle('Body', fontName=FONT, fontSize=9.5, leading=15, textColor=TEXT_PRIMARY)
style_footer = ParagraphStyle('Footer', fontName=FONT_LIGHT, fontSize=8.5, leading=13, textColor=TEXT_SECONDARY, alignment=TA_CENTER, spaceBefore=10)
style_cell = ParagraphStyle('Cell', fontName=FONT, fontSize=9, leading=14, textColor=TEXT_PRIMARY)
style_cell_bold = ParagraphStyle('CellBold', fontName=FONT_MEDIUM, fontSize=9, leading=14, textColor=PRIMARY_DARK)
style_cell_header = ParagraphStyle('CellHeader', fontName=FONT_BOLD, fontSize=9, leading=14, textColor=WHITE)
style_check = ParagraphStyle('Check', fontName=FONT_BOLD, fontSize=11, leading=15, textColor=PRIMARY, alignment=TA_CENTER)
style_note = ParagraphStyle('Note', fontName=FONT, fontSize=8.5, leading=13, textColor=HexColor('#7A5F00'))
style_code = ParagraphStyle('Code', fontName=FONT, fontSize=8, leading=12, textColor=HexColor('#0F172A'), backColor=HexColor('#F1F5F9'), leftIndent=8, rightIndent=8)


def make_header(title, subtitle, date_text):
    data = [
        [Paragraph(title, style_title)],
        [Spacer(1, 2)],
        [Paragraph(subtitle, style_subtitle)],
        [Spacer(1, 6)],
        [Paragraph(date_text, style_meta)],
    ]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_DARK),
        ('TOPPADDING', (0, 0), (0, 0), 16),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 14),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    return t


def section_title(num, title):
    return Paragraph(f"{num}. {title}", style_section)


def subsection_title(text):
    return Paragraph(text, style_subsection)


def _checkbox(size: float = 10):
    """그래픽 체크박스 — 실제 사각형 외곽선"""
    d = Drawing(size + 2, size + 2)
    d.add(Rect(1, 1, size, size, strokeColor=PRIMARY, fillColor=None, strokeWidth=1.0))
    return d


def make_check_table(headers, rows, col_widths, has_checkbox: bool = True):
    """체크박스 컬럼 포함된 표 (첫 컬럼은 그래픽 박스로 렌더링)"""
    # 헤더의 첫 컬럼이 체크 표시면 빈 헤더로 변환
    header_cells = []
    for i, h in enumerate(headers):
        if i == 0 and has_checkbox:
            header_cells.append(Paragraph("", style_cell_header))
        else:
            header_cells.append(Paragraph(h, style_cell_header))
    data = [header_cells]

    for row in rows:
        cells = []
        for i, c in enumerate(row):
            if i == 0 and has_checkbox:
                # 그래픽 체크박스로 대체
                cells.append(_checkbox(11))
            elif (i == 1 and has_checkbox) or (i == 0 and not has_checkbox):
                cells.append(Paragraph(c, style_cell_bold))
            else:
                cells.append(Paragraph(c, style_cell))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, PRIMARY_DARK),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [WHITE, SECTION_BG]),
    ]))
    return t


def info_table(rows, col_widths):
    """일반 키-값 테이블"""
    data = []
    for label, value in rows:
        data.append([Paragraph(label, style_cell_bold), Paragraph(value, style_cell)])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
    ]))
    return t


def note(text):
    data = [[Paragraph(f"<b>참고</b>&nbsp;&nbsp;{text}", style_note)]]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FFF9EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBEFOREDECOR', (0, 0), (0, -1), 3, HexColor('#E8A317')),
    ]))
    return t


# ── PDF 빌드 ──────────────────────────────────────────────────────

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    story = []

    # ── 헤더 ──────────────────────────────────────
    story.append(make_header(
        "클라이언트 인수인계 체크리스트",
        "공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발",
        "작성일: 2026-04-27 | 버전: 1.0"
    ))
    story.append(Spacer(1, 10))

    # ── 1. 시스템 개요 ─────────────────────────────
    story.append(section_title(1, "시스템 개요"))
    story.append(info_table([
        ("프로젝트명", "비드스타 (Bid Insight)"),
        ("배포 형태", "Synology NAS Docker Compose + DDNS 역방향 프록시 (HTTPS)"),
        ("외부 도메인", "Synology DDNS (예: bid-insight.synology.me) + Let's Encrypt 무료 SSL"),
        ("백엔드", "FastAPI + APScheduler + SQLite + Alembic"),
        ("프론트엔드", "React SPA (단일 HTML, 백엔드에서 정적 서빙)"),
        ("데이터 소스", "data.go.kr 나라장터 입찰공고/낙찰결과 API (G2B, 국방부 데이터 자동 포함)"),
        ("외부 의존성", "Synology 계정, data.go.kr API 키, 공인 IP + 80/443 포트포워딩"),
    ], col_widths=[35 * mm, 135 * mm]))
    story.append(Spacer(1, 10))

    # ── 2. 인수인계 산출물 ─────────────────────────
    story.append(section_title(2, "인수인계 산출물"))
    story.append(make_check_table(
        ["☐", "산출물", "위치"],
        [
            ("☐", "소스코드 전체", "/volume1/docker/bid-insight/ (Git 리포지토리)"),
            ("☐", "Dockerfile + docker-compose.prod.yml", "프로젝트 루트"),
            ("☐", "운영 환경변수 (.env)", "루트 (보안 시크릿 포함, Git 제외)"),
            ("☐", "DB 백업 (최초 시드)", "data/backups/demo-YYYYMMDD-HHMMSS.db"),
            ("☐", "NAS 배포 가이드", "docs/NAS_배포_가이드.md"),
            ("☐", "Synology DDNS 가이드", "docs/Synology_DDNS_가이드.md ★ 주 시나리오"),
            ("☐", "Cloudflare Tunnel 가이드", "docs/Cloudflare_Tunnel_가이드.md (선택)"),
            ("☐", "기능명세서 / IA 문서", "docs/기능명세서.html, docs/IA.html"),
            ("☐", "관리자 계정 정보 (1회 안전 전달)", "별도 봉인 봉투 또는 비밀번호 관리자"),
        ],
        col_widths=[12 * mm, 65 * mm, 93 * mm]
    ))
    story.append(Spacer(1, 10))

    # ── 3. NAS 환경 점검 ─────────────────────────
    story.append(section_title(3, "NAS 환경 점검"))
    story.append(make_check_table(
        ["☐", "항목", "확인 방법 / 기준"],
        [
            ("☐", "NAS 모델/OS 버전 기록", "DSM 7.x 또는 QTS 5.x"),
            ("☐", "Container Manager 설치/활성화", "DSM 패키지 센터에서 설치 확인"),
            ("☐", "RAM 4GB 이상 확보", "free -h"),
            ("☐", "여유 디스크 10GB 이상", "df -h /volume1"),
            ("☐", "관리자 SSH 접근 가능", "ssh admin@<NAS_IP> -p <port>"),
            ("☐", "외부 접속 환경 결정", "Cloudflare Tunnel / 포트포워딩 / 내부망 전용"),
        ],
        col_widths=[12 * mm, 60 * mm, 98 * mm]
    ))
    story.append(Spacer(1, 10))

    # ── 4. 배포 단계 ─────────────────────────────
    story.append(section_title(4, "배포 단계"))
    story.append(make_check_table(
        ["☐", "단계", "명령 / 비고"],
        [
            ("☐", "프로젝트 디렉토리 생성", "/volume1/docker/bid-insight/{data,backups,logs}"),
            ("☐", "코드 업로드", "rsync 또는 DSM 파일 스테이션"),
            ("☐", "운영 환경변수 작성", "cp .env.production.example .env → 필수값 입력"),
            ("☐", "SECRET_KEY 생성/입력", "openssl rand -hex 32 → SECRET_KEY="),
            ("☐", "G2B_API_KEY 입력", "data.go.kr 발급 88자 키"),
            ("☐", "Docker 이미지 빌드/실행", "docker compose -f docker-compose.prod.yml up -d --build"),
            ("☐", "DB 마이그레이션", "docker exec bid-backend python3 -m alembic upgrade head"),
            ("☐", "관리자 계정 생성", "docker exec bid-backend python3 scripts/init_admin.py --email ..."),
            ("☐", "헬스체크 200 OK", "curl http://localhost:8000/healthz"),
            ("☐", "수동 수집 검증", "관리자 로그인 → 관리자 페이지 → 수집 실행"),
        ],
        col_widths=[12 * mm, 55 * mm, 103 * mm]
    ))
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ── 5. 외부 접속 (Synology DDNS) ────────────
    story.append(section_title(5, "외부 접속 — Synology DDNS + Let's Encrypt"))
    story.append(make_check_table(
        ["☐", "단계", "비고"],
        [
            ("☐", "공인 IP 확인", "https://whatismyip.com (NAT/CGNAT 시 ISP 신청)"),
            ("☐", "DSM DDNS 호스트 등록", "외부 액세스 → DDNS → Synology → bid-insight.synology.me"),
            ("☐", "Let's Encrypt 자동 발급 체크", "DDNS 등록 시 옵션 활성화 (✓)"),
            ("☐", "공유기 포트포워딩 (80, 443)", "NAS LAN IP로 (관리포트 5000/5001 외부 차단)"),
            ("☐", "DSM 역방향 프록시 등록", "HTTPS 443 → HTTP localhost:8000"),
            ("☐", "사용자 정의 헤더 추가", "X-Real-IP, X-Forwarded-For 등 (선택)"),
            ("☐", "CORS_ORIGINS 설정", ".env에 https://bid-insight.synology.me 명시"),
            ("☐", "외부 망에서 HTTPS 접속 검증", "https://<도메인>/healthz (LTE 추천)"),
        ],
        col_widths=[12 * mm, 65 * mm, 93 * mm]
    ))
    story.append(Spacer(1, 8))
    story.append(note(
        "Cloudflare Tunnel을 사용하는 경우 docs/Cloudflare_Tunnel_가이드.md 를 참조. "
        "두 옵션 동시 운영도 가능 (CORS_ORIGINS에 콤마로 두 도메인 추가)."
    ))
    story.append(Spacer(1, 10))

    # ── 6. 자동화 / 운영 ──────────────────────────
    story.append(section_title(6, "자동화 / 운영 설정"))
    story.append(make_check_table(
        ["☐", "항목", "설정 위치"],
        [
            ("☐", "자동 수집 스케줄 활성", "관리자 페이지 → 자동 수집 설정 (매일 02:00)"),
            ("☐", "DB 백업 cron 등록", "DSM 작업 스케줄러 → 매일 03:00 backup_db.py"),
            ("☐", "외부 백업 (Hyper Backup)", "backups/ 디렉토리 → 외부 USB / 클라우드"),
            ("☐", "로그 로테이션 확인", "RotatingFileHandler 자동 (10MB × 7개)"),
            ("☐", "재시작 정책 검증", "docker inspect → restart=unless-stopped"),
            ("☐", "Cloudflare Access 정책 (선택)", "관리자 이메일 화이트리스트"),
        ],
        col_widths=[12 * mm, 65 * mm, 93 * mm]
    ))
    story.append(Spacer(1, 10))

    # ── 7. 운영 모니터링 ──────────────────────────
    story.append(section_title(7, "운영 모니터링"))
    story.append(make_check_table(
        ["☐", "지표", "확인 경로"],
        [
            ("☐", "/healthz", "{status: ok, db: ok, scheduler: running}"),
            ("☐", "/metrics", "Prometheus 포맷 (sync_success, sync_failed, users 등)"),
            ("☐", "수집 히스토리", "/admin/sync · 다크 테마로 시각 구분"),
            ("☐", "오류 모니터링", "/admin/errors · 수집 실패 로그"),
            ("☐", "NAS 디스크 사용량", "/admin/storage · 스케줄+디스크 한 화면"),
            ("☐", "컨테이너 로그", "docker logs -f bid-backend / data/server.log"),
        ],
        col_widths=[12 * mm, 50 * mm, 108 * mm]
    ))
    story.append(Spacer(1, 10))

    # ── 8. 정기 점검 ──────────────────────────────
    story.append(section_title(8, "정기 점검 항목"))
    story.append(make_check_table(
        ["주기", "항목", "기준"],
        has_checkbox=False,
        rows=[
            ("매주", "/healthz 응답", "200 OK + scheduler running"),
            ("매주", "DDNS 상태", "DSM 외부 액세스 → DDNS = '정상'"),
            ("매주", "수집 실패 건수", "sync_failed_total 증가 추이 확인"),
            ("매주", "디스크 사용량", "df -h /volume1 (80% 이하)"),
            ("매주", "백업 파일 정상", "ls -la backups/ → 최근 파일 존재"),
            ("매월", "Let's Encrypt 만료일", "DSM 인증서 → 30일 이상 남음"),
            ("매월", "Synology 계정 활성", "로그인 + 복구 이메일 갱신"),
            ("매월", "Docker 이미지 업데이트", "git pull && docker compose up -d --build"),
            ("매월", "DB 백업 복원 테스트", "별도 환경에서 backup_db.py --restore"),
            ("매월", "G2B API 키 만료 확인", "data.go.kr 마이페이지"),
            ("매분기", "비밀번호 변경", "관리자 + 모든 운영자 계정"),
        ],
        col_widths=[20 * mm, 60 * mm, 90 * mm]
    ))
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ── 9. 비상 대응 ──────────────────────────────
    story.append(section_title(9, "비상 대응 시나리오"))
    story.append(make_check_table(
        ["상황", "1차 대응", "2차 대응"],
        has_checkbox=False,
        rows=[
            ("컨테이너 다운",
             "docker compose -f docker-compose.prod.yml up -d",
             "docker logs bid-backend → 환경변수 검증"),
            ("DB 손상",
             "백업에서 복원: backup_db.py --restore <파일>",
             "Hyper Backup 외부 백업에서 복원"),
            ("API 키 만료/한도 초과",
             "data.go.kr 신규 키 발급 → .env 업데이트 → 재시작",
             "수집 임시 비활성: SYNC_ENABLED=false"),
            ("도메인 접속 불가",
             "DDNS 상태 확인 (DSM 외부 액세스), 80/443 포트포워딩 검증",
             "내부 IP 직접 접속: http://<NAS_IP>:8000"),
            ("Let's Encrypt 인증서 만료",
             "DSM 인증서 메뉴 → 수동 갱신 (80번 포트 정상이어야 함)",
             "DDNS 재등록 → 자동 발급"),
            ("디스크 full",
             "오래된 백업 정리: backup_db.py --retain 7",
             "Docker 이미지 정리: docker system prune -a"),
            ("사용자 잠금",
             "관리자 → 사용자 관리 → 활성 토글",
             "init_admin.py --update-existing 로 관리자 비번 재설정"),
        ],
        col_widths=[35 * mm, 65 * mm, 70 * mm]
    ))
    story.append(Spacer(1, 8))

    # ── 10. 연락처 ────────────────────────────────
    story.append(section_title(10, "지원 연락처"))
    story.append(info_table([
        ("기술 지원", "support@bid-insight.example.com"),
        ("긴급 장애", "전화: ___-____-____ (운영 시작 후 등록)"),
        ("data.go.kr 문의", "https://www.data.go.kr → 1:1 문의"),
        ("Cloudflare 지원", "https://support.cloudflare.com"),
        ("개발팀 GitHub", "(저장소 URL 등록)"),
    ], col_widths=[35 * mm, 135 * mm]))
    story.append(Spacer(1, 14))

    # ── 11. 인수 확인 서명란 ──────────────────────
    story.append(section_title(11, "인수 확인"))
    sign_data = [
        [Paragraph("<b>인계자</b>", style_cell_bold), Paragraph("개발사 담당자", style_cell), Paragraph("이름:", style_cell), Paragraph("서명:", style_cell)],
        [Paragraph("<b>인수자</b>", style_cell_bold), Paragraph("운영사 담당자", style_cell), Paragraph("이름:", style_cell), Paragraph("서명:", style_cell)],
        [Paragraph("<b>일시</b>", style_cell_bold), Paragraph("____년 __월 __일", style_cell), Paragraph("장소:", style_cell), Paragraph("", style_cell)],
    ]
    sign_t = Table(sign_data, colWidths=[25 * mm, 50 * mm, 45 * mm, 50 * mm])
    sign_t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(sign_t)
    story.append(Spacer(1, 16))

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "본 체크리스트는 NAS 환경에서의 운영을 위한 표준 인수인계 절차입니다.<br/>"
        "추가 질문은 위 연락처로 문의해주세요.",
        style_footer
    ))

    doc.build(story)
    print(f"✅ PDF 생성 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
