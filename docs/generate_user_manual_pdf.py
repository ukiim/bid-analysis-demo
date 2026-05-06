"""사용자 운영 매뉴얼 PDF 생성 — 비드스타 (Noto Sans KR)"""
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.enums import TA_LEFT, TA_RIGHT


# ── 폰트 ──────────────────────────────────────────────────────────
FONT_DIR = os.path.expanduser("~/Library/Fonts")
pdfmetrics.registerFont(TTFont('NotoSansKR', os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Bold', os.path.join(FONT_DIR, 'NotoSansKR-Bold.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Medium', os.path.join(FONT_DIR, 'NotoSansKR-Medium.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Light', os.path.join(FONT_DIR, 'NotoSansKR-Light.ttf')))
registerFontFamily('NotoSansKR', normal='NotoSansKR', bold='NotoSansKR-Bold')

FONT, FONT_BOLD, FONT_MEDIUM, FONT_LIGHT = (
    'NotoSansKR', 'NotoSansKR-Bold', 'NotoSansKR-Medium', 'NotoSansKR-Light',
)

# ── 색상 (서비스: 파랑, 관리자 안내: 빨강) ────────────────────────
PRIMARY = HexColor('#0066CC')
PRIMARY_DARK = HexColor('#1A3353')
ADMIN_RED = HexColor('#DC2626')
LIGHT_BG = HexColor('#F0F5FB')
ADMIN_BG = HexColor('#FEE2E2')
BORDER = HexColor('#D0D7E3')
TEXT_PRIMARY = HexColor('#222831')
TEXT_SECONDARY = HexColor('#5A6A7E')
SECTION_BG = HexColor('#F7F9FC')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "비드스타_사용자_운영_매뉴얼.pdf")

# ── 스타일 ────────────────────────────────────────────────────────
S_TITLE = ParagraphStyle('Title', fontName=FONT_BOLD, fontSize=22, leading=28, textColor=white)
S_SUB = ParagraphStyle('Sub', fontName=FONT, fontSize=11, leading=15, textColor=HexColor('#B0C4DE'))
S_META = ParagraphStyle('Meta', fontName=FONT_LIGHT, fontSize=9, leading=13, textColor=HexColor('#B0C4DE'), alignment=TA_RIGHT)
S_H1 = ParagraphStyle('H1', fontName=FONT_BOLD, fontSize=15, leading=20, textColor=PRIMARY_DARK, spaceBefore=14, spaceAfter=8)
S_H2 = ParagraphStyle('H2', fontName=FONT_BOLD, fontSize=12, leading=17, textColor=PRIMARY, spaceBefore=10, spaceAfter=5)
S_BODY = ParagraphStyle('Body', fontName=FONT, fontSize=10, leading=15.5, textColor=TEXT_PRIMARY, spaceAfter=4)
S_BULLET = ParagraphStyle('Bullet', fontName=FONT, fontSize=10, leading=15, textColor=TEXT_PRIMARY, leftIndent=14, bulletIndent=4, spaceAfter=2)
S_NOTE = ParagraphStyle('Note', fontName=FONT, fontSize=9, leading=14, textColor=HexColor('#7A5F00'))
S_FOOTER = ParagraphStyle('Footer', fontName=FONT_LIGHT, fontSize=8.5, leading=13, textColor=TEXT_SECONDARY, alignment=1, spaceBefore=8)
S_CELL = ParagraphStyle('Cell', fontName=FONT, fontSize=9.5, leading=14, textColor=TEXT_PRIMARY)
S_CELL_BOLD = ParagraphStyle('CellBold', fontName=FONT_MEDIUM, fontSize=9.5, leading=14, textColor=PRIMARY_DARK)
S_CELL_HDR = ParagraphStyle('CellHdr', fontName=FONT_BOLD, fontSize=9.5, leading=14, textColor=white)


def header_block():
    data = [
        [Paragraph("비드스타 사용자 운영 매뉴얼", S_TITLE)],
        [Spacer(1, 4)],
        [Paragraph("공공데이터 기반 입찰가 산정 및 사정률 분석 플랫폼", S_SUB)],
        [Spacer(1, 8)],
        [Paragraph("작성일: 2026-04-29 · 버전 1.0", S_META)],
    ]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), PRIMARY_DARK),
        ('TOPPADDING', (0, 0), (0, 0), 18),
        ('LEFTPADDING', (0, 0), (-1, -1), 22),
        ('RIGHTPADDING', (0, 0), (-1, -1), 22),
        ('BOTTOMPADDING', (-1, -1), (-1, -1), 16),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [8, 8, 8, 8]),
    ]))
    return t


def section_h1(num, title):
    return Paragraph(f"{num}. {title}", S_H1)


def section_h2(title):
    return Paragraph(title, S_H2)


def body(text):
    return Paragraph(text, S_BODY)


def bullets(items):
    return [Paragraph(f"• {it}", S_BULLET) for it in items]


def kv_table(rows, col_widths=None, header_color=PRIMARY):
    if col_widths is None:
        col_widths = [40 * mm, 130 * mm]
    data = []
    for label, value in rows:
        data.append([Paragraph(label, S_CELL_BOLD), Paragraph(value, S_CELL)])
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_BG),
    ]))
    return t


def step_table(headers, rows, col_widths, accent=PRIMARY):
    data = [[Paragraph(h, S_CELL_HDR) for h in headers]]
    for row in rows:
        cells = [Paragraph(str(c), S_CELL_BOLD if i == 0 else S_CELL) for i, c in enumerate(row)]
        data.append(cells)
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), accent),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, PRIMARY_DARK),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 9),
        ('RIGHTPADDING', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [white, SECTION_BG]),
    ]))
    return t


def note(text, accent=HexColor('#E8A317')):
    data = [[Paragraph(f"<b>참고</b>&nbsp;&nbsp;{text}", S_NOTE)]]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#FFF9EB')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('LINEBEFOREDECOR', (0, 0), (0, -1), 3, accent),
    ]))
    return t


def admin_callout(text):
    """관리자 영역 안내 — 빨간 박스"""
    data = [[Paragraph(f"<b>관리자 전용</b>&nbsp;&nbsp;{text}", S_NOTE)]]
    t = Table(data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ADMIN_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('LINEBEFOREDECOR', (0, 0), (0, -1), 3, ADMIN_RED),
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

    # ── 헤더 ───────────────────────────────────────
    story.append(header_block())
    story.append(Spacer(1, 14))

    # ── 1. 시작하기 ─────────────────────────────────
    story.append(section_h1(1, "시작하기"))
    story.append(body(
        "비드스타는 공공데이터(나라장터)를 기반으로 입찰 사정률을 분석·예측하는 웹 플랫폼입니다. "
        "본 매뉴얼은 일반 사용자와 관리자 모두를 위한 운영 가이드입니다."
    ))
    story.append(section_h2("1-1. 접속 정보"))
    story.append(kv_table([
        ("서비스 주소", "https://&lt;NAS DDNS 도메인&gt; (예: bid-insight.synology.me)"),
        ("브라우저 권장", "Chrome 120+ / Edge 120+ / Safari 16+"),
        ("모바일", "동일 URL — 반응형 자동 적용 (768px 이하)"),
    ]))
    story.append(Spacer(1, 6))
    story.append(section_h2("1-2. 처음 로그인"))
    story.extend(bullets([
        "관리자에게서 받은 이메일·비밀번호로 로그인",
        "비밀번호는 첫 로그인 후 즉시 마이페이지에서 변경 권장",
        "이메일·비밀번호 분실 시 관리자에게 재설정 요청",
    ]))
    story.append(Spacer(1, 12))

    # ── 2. 메뉴 구조 ────────────────────────────────
    story.append(section_h1(2, "메뉴 구조"))
    story.append(body(
        "사이드바는 <b>서비스</b>와 <b>관리</b> 두 섹션으로 나뉩니다. "
        "관리자 메뉴는 관리자 권한이 있는 사용자에게만 표시됩니다."
    ))
    story.append(step_table(
        ["섹션", "메뉴", "URL", "설명"],
        [
            ("서비스", "공고 화면",     "/announcements", "전체 공고 목록 + 필터 + 상세 미리보기"),
            ("서비스", "종합 분석",     "/comprehensive", "Tab1 빈도 / Tab2 갭 / Tab3 종합 분석"),
            ("서비스", "마이 페이지",   "/mypage", "프로필 / 비밀번호 변경 / 내 분석 이력"),
            ("서비스", "데이터 업로드", "/upload", "엑셀·CSV 업로드, 검증, 이력"),
            ("관리",   "관리자",       "/admin", "관리자 콘솔 (4개 서브 페이지)"),
        ],
        col_widths=[18 * mm, 30 * mm, 35 * mm, 87 * mm],
    ))
    story.append(Spacer(1, 10))

    # ── 3. 공고 화면 사용법 ─────────────────────────
    story.append(section_h1(3, "공고 화면 사용법"))
    story.append(section_h2("3-1. 필터 및 검색"))
    story.extend(bullets([
        "키워드 검색: 공고명, 발주기관 둘 다 검색됨",
        "유형 필터: 공사 / 용역 (현재 운영 카테고리)",
        "지역 필터: 17개 시도",
        "고급 필터 ▼ 클릭 시 일자 범위, 공종, 출처 등 추가",
        "필터를 모두 적용하면 우측 상단에 결과 건수 표시",
    ]))
    story.append(section_h2("3-2. 공고 상세 미리보기"))
    story.extend(bullets([
        "테이블 행 클릭 → 우측에서 미리보기 패널 슬라이드",
        "모바일에서는 하단에서 시트로 올라옴",
        "<b>예상 투찰금액 계산기</b>: 사정률 입력 → 자동 계산",
        "<b>공고 바로가기 ↗</b>: 나라장터(G2B) 원본 공고로 새 탭 이동",
        "<b>상세 분석 (종합화면)</b>: Tab1/2/3 종합 분석 화면으로 이동",
    ]))
    story.append(note(
        "<b>비공개</b>로 표시된 기초금액은 G2B에서 협상/외자 사유로 미공개된 공고입니다. 정상입니다."
    ))
    story.append(Spacer(1, 10))

    # ── 4. 종합 분석 사용법 ─────────────────────────
    story.append(section_h1(4, "종합 분석 사용법"))
    story.append(body(
        "종합 분석은 3개 탭으로 구성되어 있습니다. 일반적인 흐름은 Tab1 → Tab2 → Tab3 순으로 진행됩니다."
    ))
    story.append(section_h2("Tab 1. 사정률 발생빈도 + 구간 분석"))
    story.extend(bullets([
        "막대 클릭으로 사정률 선택",
        "기간(최근 N개월), 발주기관 범위(특정/상위) 조절",
        "1순위 예측 후보 리스트에서 추천 사정률(★) 확인",
    ]))
    story.append(section_h2("Tab 2. 업체 사정률 + 갭 분석"))
    story.extend(bullets([
        "선택 구간 내 업체 투찰률 분포 표시",
        "최대 갭 중간점이 자동 계산되어 정밀 사정률 제안",
        "차기연도 검증 표로 적중률 확인",
    ]))
    story.append(section_h2("Tab 3. 종합 분석 + 결합 예측"))
    story.extend(bullets([
        "확정 사정률 입력 시 1순위 예상 낙찰가 즉시 계산",
        "기초금액이 0/비공개인 공고는 '산출 불가' 안내 (사정률 분석은 정상)",
        "밀어내기식 검토 + 연도별 검증으로 안정성 평가",
    ]))
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ── 5. 마이페이지 ────────────────────────────────
    story.append(section_h1(5, "마이페이지"))
    story.extend(bullets([
        "프로필 정보(이메일·역할·플랜·분석 횟수) 표시",
        "비밀번호 변경: 현재 → 새 비밀번호 두 번 입력",
        "분석 이력 테이블: 최근 분석한 공고와 사정률 기록",
        "이력 행 클릭 시 해당 공고 분석 화면으로 즉시 이동",
    ]))
    story.append(Spacer(1, 10))

    # ── 6. 데이터 업로드 ────────────────────────────
    story.append(section_h1(6, "데이터 업로드"))
    story.append(body(
        "과거 입찰 데이터를 엑셀(.xlsx) 또는 CSV로 일괄 업로드할 수 있습니다."
    ))
    story.append(section_h2("필수 컬럼"))
    story.append(kv_table([
        ("공고번호", "필수 — 중복 검사 기준 (G2B 형식 권장)"),
        ("공고명", "필수 — 한글 가능"),
        ("발주기관", "필수 — 정확한 명칭"),
        ("기초금액", "필수 — 숫자(원 단위), 미공개는 0 또는 빈칸"),
    ]))
    story.append(section_h2("업로드 절차"))
    story.extend(bullets([
        "파일을 드래그하거나 클릭하여 선택 (10MB 이하)",
        "자동 검증: 필수 컬럼 / 중복(공고번호) / 행별 오류 표시",
        "유효 N건 / 중복 N건 / 오류 N건 요약 표시",
        "오류 행은 행번호 + 사유와 함께 최대 50건 안내",
        "업로드 이력은 사용자별로 보존 (관리자만 전체 조회 가능)",
    ]))
    story.append(note(
        "엑셀 인코딩이 cp949인 경우도 자동 감지하여 처리합니다. UTF-8 권장."
    ))
    story.append(Spacer(1, 12))

    # ── 7. 관리자 콘솔 ──────────────────────────────
    story.append(section_h1(7, "관리자 콘솔"))
    story.append(admin_callout(
        "관리자 영역은 사이드바 '관리자' 메뉴 클릭 또는 URL <b>/admin</b> 직접 입력으로 진입합니다. "
        "진입 즉시 화면 전체가 <b>다크 테마 + 빨간 강조색</b>으로 전환되어 영역 변화가 명확히 인지됩니다."
    ))
    story.append(Spacer(1, 8))
    story.append(section_h2("4개 서브 페이지"))
    story.append(step_table(
        ["페이지", "URL", "기능"],
        [
            ("사용자 관리",     "/admin",         "이메일 검색, 활성/비활성 토글"),
            ("데이터 수집",     "/admin/sync",    "수동 수집 실행, 수집 추이 차트, 히스토리, 재시도"),
            ("스토리지·스케줄", "/admin/storage", "자동 수집 스케줄(매시/매일/매주) + NAS 디스크 사용량"),
            ("오류 모니터링",   "/admin/errors",  "수집 실패 로그와 상세 오류 메시지"),
        ],
        col_widths=[35 * mm, 35 * mm, 100 * mm],
        accent=ADMIN_RED,
    ))
    story.append(Spacer(1, 8))
    story.append(section_h2("관리자 알림 (선택)"))
    story.extend(bullets([
        "자동 수집 실패 시 Slack/Discord webhook 알림 (.env의 ALERT_WEBHOOK_URL)",
        "이메일 알림 (.env의 ALERT_EMAIL_TO + SMTP_HOST)",
        "최근 N회 중 실패율 K% 초과 시 별도 알림 (ALERT_FAILURE_THRESHOLD)",
    ]))
    story.append(Spacer(1, 10))

    # ── 8. 자주 묻는 질문 ───────────────────────────
    story.append(section_h1(8, "자주 묻는 질문 (FAQ)"))
    story.append(step_table(
        ["질문", "답변"],
        [
            ("로그인이 안 됩니다.", "관리자에게 비밀번호 재설정 요청. 이메일 오타 확인."),
            ("공고가 갱신이 안 됩니다.", "관리자 페이지 → 데이터 수집 → '수동 수집' 실행. 자동 수집은 매일 02:00."),
            ("기초금액이 '비공개'로 보여요.", "G2B에서 협상/외자/의료장비 등의 사유로 미공개된 정상 케이스입니다."),
            ("모바일에서 사이드바가 안 보여요.", "좌측 상단 햄버거(≡) 버튼 탭 → 사이드바 슬라이드"),
            ("관리자 메뉴가 안 보여요.", "관리자 권한이 부여되지 않았습니다. 관리자에게 요청"),
            ("CSV 업로드 시 깨져요.", "엑셀에서 'CSV UTF-8' 형식으로 저장. 또는 .xlsx로 업로드"),
            ("URL 직접 진입 시 404", "정상 동작. 새로고침/북마크 모두 지원합니다."),
        ],
        col_widths=[55 * mm, 115 * mm],
    ))
    story.append(Spacer(1, 14))

    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "본 매뉴얼은 비드스타 v1.0 기준입니다. 추가 문의는 시스템 관리자에게 연락주세요.",
        S_FOOTER,
    ))

    doc.build(story)
    print(f"✅ PDF 생성 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
