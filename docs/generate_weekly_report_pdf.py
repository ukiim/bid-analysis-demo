"""주간 업무보고 PDF 생성 스크립트 — Noto Sans KR"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

# ── Register Noto Sans KR fonts ──────────────────────────────────────
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

# ── Colors ────────────────────────────────────────────────────────────
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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "주간업무보고_1주차.pdf")

# ── Styles ────────────────────────────────────────────────────────────
style_title = ParagraphStyle(
    'Title', fontName=FONT_BOLD, fontSize=20, leading=26,
    textColor=WHITE, alignment=TA_LEFT,
)
style_subtitle = ParagraphStyle(
    'Subtitle', fontName=FONT, fontSize=10, leading=14,
    textColor=HexColor('#B0C4DE'), alignment=TA_LEFT,
)
style_meta = ParagraphStyle(
    'Meta', fontName=FONT_LIGHT, fontSize=9, leading=13,
    textColor=HexColor('#B0C4DE'), alignment=TA_RIGHT,
)
style_section = ParagraphStyle(
    'Section', fontName=FONT_BOLD, fontSize=14, leading=19,
    textColor=PRIMARY_DARK, spaceBefore=14, spaceAfter=8,
)
style_subsection = ParagraphStyle(
    'Subsection', fontName=FONT_BOLD, fontSize=11, leading=16,
    textColor=PRIMARY, spaceBefore=10, spaceAfter=5,
)
style_footer = ParagraphStyle(
    'Footer', fontName=FONT_LIGHT, fontSize=8.5, leading=13,
    textColor=TEXT_SECONDARY, alignment=TA_CENTER, spaceBefore=10,
)
style_cell = ParagraphStyle(
    'Cell', fontName=FONT, fontSize=9.5, leading=15,
    textColor=TEXT_PRIMARY,
)
style_cell_bold = ParagraphStyle(
    'CellBold', fontName=FONT_MEDIUM, fontSize=9.5, leading=15,
    textColor=PRIMARY_DARK,
)
style_cell_header = ParagraphStyle(
    'CellHeader', fontName=FONT_BOLD, fontSize=9.5, leading=14,
    textColor=WHITE,
)
style_bullet = ParagraphStyle(
    'Bullet', fontName=FONT, fontSize=9, leading=14,
    textColor=TEXT_PRIMARY, leftIndent=14, bulletIndent=4,
)


# ── Building blocks ──────────────────────────────────────────────────

def make_header_block():
    header_data = [
        [Paragraph("주간 업무보고 — 1주차", style_title)],
        [Spacer(1, 2)],
        [Paragraph("공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발", style_subtitle)],
        [Spacer(1, 8)],
        [Paragraph(
            "기간: 2026-04-20 ~ 2026-04-24&nbsp;&nbsp;|&nbsp;&nbsp;작성일: 2026-04-24&nbsp;&nbsp;|&nbsp;&nbsp;작성자: 김동욱",
            style_meta
        )],
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


def make_subsection_title(text):
    return Paragraph(text, style_subsection)


def make_table(headers, rows, col_widths):
    data = [[Paragraph(h, style_cell_header) for h in headers]]
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            style = style_cell_bold if i == 0 else style_cell
            cells.append(Paragraph(str(cell), style))
        data.append(cells)

    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, PRIMARY_DARK),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (1, 1), (-1, -1), [WHITE, SECTION_BG]),
    ]))
    return t


def make_bullet_list(items):
    flow = []
    for item in items:
        flow.append(Paragraph(f"• {item}", style_bullet))
    return flow


def make_progress_bar(percentage, width=40 * mm, height=6):
    """Simple progress bar drawn as a table"""
    from reportlab.platypus import Table as Tbl
    filled_w = width * (percentage / 100.0)
    empty_w = width - filled_w
    if empty_w < 0.1:
        data = [['']]
        t = Tbl(data, colWidths=[width], rowHeights=[height])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), PRIMARY),
            ('LINEBELOW', (0, 0), (-1, -1), 0, WHITE),
        ]))
    else:
        data = [['', '']]
        t = Tbl(data, colWidths=[filled_w, empty_w], rowHeights=[height])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), PRIMARY),
            ('BACKGROUND', (1, 0), (1, 0), HexColor('#E5EAF1')),
            ('LINEBELOW', (0, 0), (-1, -1), 0, WHITE),
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

    # ── 1. 이번 주 완료 작업 ─────────────────────────
    story.append(make_section_title(1, "이번 주 완료 작업"))

    # 1-1
    story.append(make_subsection_title("1-1. 프로젝트 착수 및 설계"))
    story.append(make_table(
        ["구분", "내용"],
        [
            ["킥오프", "프로젝트 범위·일정·산출물 확정"],
            ["아키텍처 정의", "NAS 기반 Docker 배포 구조, FastAPI + SQLite + React SPA 단일 파일 구조 확정"],
            ["IA 문서 v3.0", "전체 8개 화면(인증/공고/분석 Tab1~3/마이페이지/업로드/관리자) 정보구조 정리"],
            ["기능명세서", "각 화면별 기능·API·권한 매트릭스 작성"],
            ["클라이언트 요청사항", "NAS 환경·API 키·도메인·기존 데이터·운영·디자인 6개 항목 PDF 전달"],
        ],
        col_widths=[40 * mm, 130 * mm]
    ))

    # 1-2
    story.append(make_subsection_title("1-2. 백엔드 초기 구성"))
    story.append(make_table(
        ["구분", "내용"],
        [
            ["프로젝트 스캐폴드", "FastAPI 프로젝트 구조 셋업, SQLite 기반 개발 DB 설정"],
            ["인증 시스템", "JWT + bcrypt 기반 로그인/회원가입/토큰 갱신 구현"],
            ["기본 DB 모델", "User 모델 및 주요 엔티티 스키마 설계"],
            ["보안 기초", "CORS·SECRET_KEY 환경변수화, 관리자 엔드포인트 권한 의존성 추가"],
        ],
        col_widths=[40 * mm, 130 * mm]
    ))

    # 1-3
    story.append(make_subsection_title("1-3. 프론트엔드 초기 구성"))
    story.append(make_table(
        ["구분", "내용"],
        [
            ["프로젝트 스캐폴드", "React SPA 단일 파일 구조 셋업, 라우팅 기본 구성"],
            ["레이아웃 골격", "헤더·사이드바·콘텐츠 영역 기본 레이아웃 구현"],
            ["인증 플로우", "로그인/회원가입 화면 및 AuthContext 연동"],
            ["사이드바 메뉴", "서비스/관리 2개 섹션, 5개 메뉴 체계 초안 반영"],
        ],
        col_widths=[40 * mm, 130 * mm]
    ))

    story.append(Spacer(1, 8))

    # ── 2. 다음 주 작업 계획 ─────────────────────────
    story.append(make_section_title(2, "다음 주 작업 계획 (2주차: 04-27 ~ 05-01)"))

    next_week = [
        ["공공데이터 API 연동", "나라장터(G2B) 입찰공고·개찰결과 API 연동, 오류 처리/재시도, Rate Limit 대응"],
        ["자동 수집 배치", "APScheduler 기반 수집 배치(매시/매일/매주), 결과 SyncHistory 기록, 실패 알림"],
        ["분석 엔진 1차", "Tab1 빈도 분석, Tab2 갭 분석, Tab3 종합 분석 (예측 후보/검증 테이블)"],
        ["NAS 환경 준비", "NAS 사양 확인(클라이언트 회신), Docker Compose 초안, Cloudflare Tunnel 가이드"],
        ["테스트 및 QA", "pytest 단위 테스트, Playwright E2E 시나리오 초안, 1차 검수 체크리스트"],
    ]
    story.append(make_table(
        ["작업 항목", "세부 내용"],
        next_week,
        col_widths=[45 * mm, 125 * mm]
    ))

    story.append(Spacer(1, 8))

    # ── 3. 진행률 요약 ───────────────────────────────
    story.append(make_section_title(3, "진행률 요약"))

    progress_rows = [
        ("설계 / 문서", 100, "IA v3.0, 기능명세서, 클라이언트 요청사항 PDF 전달 완료"),
        ("백엔드 API", 15, "스캐폴드·인증·기본 DB 모델 구성, 공공데이터 연동/분석 엔진 미착수"),
        ("프론트엔드", 10, "레이아웃 골격·인증 플로우 구성, 주요 화면 UI 및 분석 Tab 잔여"),
        ("배포 / 인프라", 0, "NAS 환경 확보 대기, 본격 착수 전"),
        ("전체", 20, "착수 단계 진행 중 (설계 완료, 구현 초기)"),
    ]

    data = [[
        Paragraph("구분", style_cell_header),
        Paragraph("진행률", style_cell_header),
        Paragraph("%", style_cell_header),
        Paragraph("비고", style_cell_header),
    ]]
    for name, pct, note in progress_rows:
        data.append([
            Paragraph(name, style_cell_bold),
            make_progress_bar(pct, width=48 * mm, height=8),
            Paragraph(f"{pct}%", style_cell_bold),
            Paragraph(note, style_cell),
        ])

    t = Table(data, colWidths=[32 * mm, 55 * mm, 18 * mm, 65 * mm], repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('LINEBELOW', (0, 0), (-1, 0), 1.2, PRIMARY_DARK),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('TOPPADDING', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 9),
        ('TOPPADDING', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 1), (0, -1), LIGHT_BG),
        ('ROWBACKGROUNDS', (1, 1), (-1, -2), [WHITE, SECTION_BG]),
        # Highlight total row
        ('BACKGROUND', (0, -1), (-1, -1), HexColor('#FFF4D6')),
        ('LINEABOVE', (0, -1), (-1, -1), 1.0, ACCENT_AMBER),
    ]))
    story.append(t)

    story.append(Spacer(1, 10))

    # ── Footer ───────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER, spaceBefore=2, spaceAfter=6))
    story.append(Paragraph(
        "작성자: 김동욱 (kdw830@firstpip.co.kr)",
        style_footer
    ))

    doc.build(story)
    print(f"PDF 생성 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    build_pdf()
