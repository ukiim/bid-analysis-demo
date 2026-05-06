"""클라이언트 요청사항 PDF 생성 스크립트 — Noto Sans KR (2페이지)"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    KeepTogether, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Register Noto Sans KR fonts (TTF) ────────────────────────────────
FONT_DIR = os.path.expanduser("~/Library/Fonts")
pdfmetrics.registerFont(TTFont('NotoSansKR', os.path.join(FONT_DIR, 'NotoSansKR-Regular.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Bold', os.path.join(FONT_DIR, 'NotoSansKR-Bold.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Medium', os.path.join(FONT_DIR, 'NotoSansKR-Medium.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-Light', os.path.join(FONT_DIR, 'NotoSansKR-Light.ttf')))
pdfmetrics.registerFont(TTFont('NotoSansKR-SemiBold', os.path.join(FONT_DIR, 'NotoSansKR-SemiBold.ttf')))

from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily('NotoSansKR', normal='NotoSansKR', bold='NotoSansKR-Bold')

FONT = 'NotoSansKR'
FONT_BOLD = 'NotoSansKR-Bold'
FONT_MEDIUM = 'NotoSansKR-Medium'
FONT_LIGHT = 'NotoSansKR-Light'

# ── Colors ────────────────────────────────────────────────────────────
PRIMARY = HexColor('#0066CC')
PRIMARY_DARK = HexColor('#1A3353')
LIGHT_BG = HexColor('#F0F5FB')
BORDER = HexColor('#D0D7E3')
TEXT_PRIMARY = HexColor('#222831')
TEXT_SECONDARY = HexColor('#5A6A7E')
WHITE = white
SECTION_BG = HexColor('#F7F9FC')
NOTE_BG = HexColor('#FFF9EB')
NOTE_BORDER = HexColor('#E8A317')

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "클라이언트_요청사항.pdf")

# ── Styles (compact for 2-page layout) ───────────────────────────────
style_title = ParagraphStyle(
    'Title', fontName=FONT_BOLD, fontSize=20, leading=26,
    textColor=WHITE, alignment=TA_LEFT,
)
style_subtitle = ParagraphStyle(
    'Subtitle', fontName=FONT, fontSize=10, leading=14,
    textColor=HexColor('#B0C4DE'), alignment=TA_LEFT,
)
style_date = ParagraphStyle(
    'Date', fontName=FONT_LIGHT, fontSize=8, leading=11,
    textColor=HexColor('#8FA4BD'), alignment=TA_RIGHT,
)
style_section = ParagraphStyle(
    'Section', fontName=FONT_BOLD, fontSize=12, leading=16,
    textColor=PRIMARY_DARK, spaceBefore=10, spaceAfter=4,
)
style_note = ParagraphStyle(
    'Note', fontName=FONT, fontSize=8, leading=12,
    textColor=HexColor('#7A5F00'),
)
style_footer = ParagraphStyle(
    'Footer', fontName=FONT, fontSize=9, leading=14,
    textColor=TEXT_SECONDARY, alignment=TA_CENTER, spaceBefore=12,
)
style_cell = ParagraphStyle(
    'Cell', fontName=FONT, fontSize=8.5, leading=13,
    textColor=TEXT_PRIMARY,
)
style_cell_bold = ParagraphStyle(
    'CellBold', fontName=FONT_MEDIUM, fontSize=8.5, leading=13,
    textColor=TEXT_PRIMARY,
)
style_cell_header = ParagraphStyle(
    'CellHeader', fontName=FONT_BOLD, fontSize=8.5, leading=13,
    textColor=WHITE,
)


# ── Building blocks ──────────────────────────────────────────────────

def make_header_block():
    header_data = [
        [Paragraph("클라이언트 요청사항", style_title)],
        [Spacer(1, 2)],
        [Paragraph("공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발", style_subtitle)],
        [Spacer(1, 6)],
        [Paragraph("작성일: 2026-04-19", style_date)],
    ]
    t = Table(header_data, colWidths=[170 * mm])
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


def make_section_title(number, title):
    return Paragraph(f"{number}. {title}", style_section)


def make_table(headers, rows, col_widths=None):
    if col_widths is None:
        col_widths = [42 * mm, 128 * mm]

    data = []
    header_row = [Paragraph(f"{h}", style_cell_header) for h in headers]
    data.append(header_row)

    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            style = style_cell_bold if i == 0 else style_cell
            cells.append(Paragraph(str(cell), style))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)

    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [WHITE, SECTION_BG]),
    ]
    t.setStyle(TableStyle(style_cmds))
    return t


def make_note(text):
    note_data = [[Paragraph(f"<b>참고</b>&nbsp;&nbsp;{text}", style_note)]]
    t = Table(note_data, colWidths=[170 * mm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), NOTE_BG),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('LINEBEFOREDECOR', (0, 0), (0, -1), 3, NOTE_BORDER),
    ]))
    return t


# ── Build PDF ─────────────────────────────────────────────────────────

def build_pdf():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
    )

    story = []

    # ── Header ───────────────────────────────────────
    story.append(make_header_block())
    story.append(Spacer(1, 10))

    # ── 1. NAS 서버 환경 정보 ────────────────────────
    story.append(make_section_title(1, "NAS 서버 환경 정보"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["NAS 모델", "Synology / QNAP 등 모델명 (예: DS920+, TS-453D)"],
            ["OS 버전", "DSM 7.x / QTS 5.x 등 현재 설치된 OS 버전"],
            ["CPU / RAM", "프로세서 종류 및 메모리 용량"],
            ["가용 저장공간", "Docker 및 데이터 저장에 사용할 수 있는 디스크 여유 공간"],
            ["Docker 지원 여부", "Docker(Container Station) 설치 가능 여부 확인"],
            ["외부 접속 환경", "고정 IP 사용 여부, 공유기 포트포워딩 가능 여부, Cloudflare Tunnel 사용 의향"],
        ]
    ))
    story.append(Spacer(1, 6))

    # ── 2. 공공데이터 API 키 ─────────────────────────
    story.append(make_section_title(2, "공공데이터 API 키"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["공공데이터포털 API 키", "data.go.kr 회원가입 후 발급받은 인증키 (일반 인증키)"],
            ["국방조달(D2B) API", "D2B 데이터 연동이 필요한 경우 별도 API 키 발급 필요 여부 확인"],
        ]
    ))
    story.append(Spacer(1, 4))
    story.append(make_note(
        'API 키가 없는 경우 공공데이터포털(data.go.kr)에서 회원가입 후 '
        '"나라장터 입찰공고정보" 및 "개찰결과정보" API 활용 신청 후 인증키를 전달해주시면 됩니다.'
    ))
    story.append(Spacer(1, 6))

    # ── 3. 도메인 및 SSL ─────────────────────────────
    story.append(make_section_title(3, "도메인 및 SSL"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["사용할 도메인", "서비스 접속에 사용할 도메인 (예: bid.example.com)"],
            ["도메인 보유 여부", "기존 보유 도메인이 있는지, 신규 구매가 필요한지"],
            ["SSL 인증서", "Cloudflare Tunnel 사용 시 자동 적용되며, 별도 인증서 보유 시 전달 요청"],
        ]
    ))
    story.append(Spacer(1, 6))

    # ── 4. 기존 데이터 제공 ──────────────────────────
    story.append(make_section_title(4, "기존 데이터 제공"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["과거 입찰 데이터", "2019년~현재까지의 과거 입찰 데이터(공고/낙찰결과)가 있는 경우 Excel 또는 CSV 형태로 제공 요청"],
            ["데이터 형식", "최소 필수 컬럼: 공고번호, 공고명, 발주기관, 기초금액, 사정률, 낙찰금액"],
            ["업체 투찰 기록", "업체별 투찰률/투찰금액 데이터가 있는 경우 함께 제공"],
        ]
    ))
    story.append(Spacer(1, 4))
    story.append(make_note(
        '기존 데이터가 없는 경우 API 연동 후 자동 수집으로 데이터를 축적합니다.'
    ))
    story.append(Spacer(1, 6))

    # ── 5. 운영 관련 확인 ────────────────────────────
    story.append(make_section_title(5, "운영 관련 확인"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["관리자 계정", "관리자 이메일 주소 (초기 관리자 계정 생성에 사용)"],
            ["사용자 수 예상", "동시 접속 사용자 수 예상치 (NAS 리소스 최적화에 필요)"],
            ["데이터 수집 주기", "원하는 자동 수집 주기 (매시/매일/매주) 및 수집 시간대"],
            ["백업 정책", "NAS 내 자동 백업 주기 희망 사항 (일간/주간)"],
        ]
    ))
    story.append(Spacer(1, 6))

    # ── 6. 디자인 관련 ───────────────────────────────
    story.append(make_section_title(6, "디자인 관련"))
    story.append(make_table(
        ["항목", "설명"],
        [
            ["로고/CI", "서비스에 사용할 로고 이미지 파일 (PNG/SVG, 투명 배경 권장)"],
            ["서비스명", '현재 "비드스타"로 설정되어 있으며, 변경 희망 시 전달'],
            ["브랜드 컬러", "선호 색상이 있는 경우 전달 (현재: 파란색 계열 #0066CC)"],
        ]
    ))
    story.append(Spacer(1, 12))

    # ── Footer ───────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=4, spaceAfter=6))
    story.append(Paragraph(
        "위 사항을 확인하시어 회신 부탁드립니다. 추가 문의사항이 있으시면 언제든 연락 주세요.",
        style_footer
    ))

    doc.build(story)
    print(f"PDF 생성 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
