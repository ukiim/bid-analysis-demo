"""주간 업무보고 2주차 PDF 생성 스크립트 — Noto Sans KR"""

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

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "주간업무보고_2주차.pdf")

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
        [Paragraph("주간 업무보고 — 2주차", style_title)],
        [Spacer(1, 2)],
        [Paragraph("공공데이터 기반 입찰가 산정 및 사정률 분석 웹 개발", style_subtitle)],
        [Spacer(1, 8)],
        [Paragraph(
            "기간: 2026-04-27 ~ 2026-05-01&nbsp;&nbsp;|&nbsp;&nbsp;갱신일: 2026-05-01&nbsp;&nbsp;|&nbsp;&nbsp;작성자: 김동욱",
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
    story.append(make_section_title(1, "2주차 완료 현황"))

    # 1-1 백엔드
    story.append(make_subsection_title("1-1. 백엔드"))
    backend_done = [
        [
            "공공데이터 실 API 연동",
            "완료",
            "조달청 나라장터(용역·공사) + 국방부 통합 수집 — 공고 약 18.3만건, 낙찰결과 3천여 건 적재 (2023~2026년분, 2019년까지 점진적 적재 진행 중)",
        ],
        [
            "자동 수집·알림",
            "완료",
            "매일 자동 수집 배치, 수집 이력 저장, 실패 임계치 초과 시 운영자 알림",
        ],
        [
            "사정률 예측 로직",
            "완료",
            "사정률 발생빈도 분석, 업체 갭 분석, 종합 상관관계 분석으로 1순위 예측값 산출. 사용자별 분석 조건 저장과 분석 결과 엑셀 내보내기 지원",
        ],
        [
            "데이터 보존·증분 수집",
            "완료",
            "10년 자동 보관 정책 적용, 직전 수집 시점 이후만 다시 받는 증분 모드 도입, 주간 자동 정리 작업 등록",
        ],
        [
            "백엔드 테스트",
            "완료",
            "단위·기능·시나리오 자동 테스트 92건 모두 통과",
        ],
        [
            "보안 강화",
            "완료",
            "관리자 전용 기능 권한 검증 일괄 적용, 운영 비밀값 환경변수 분리",
        ],
    ]
    story.append(make_table(
        ["작업 항목", "상태", "2주차 결과"],
        backend_done,
        col_widths=[42 * mm, 20 * mm, 108 * mm]
    ))

    # 1-2 프론트엔드
    story.append(make_subsection_title("1-2. 프론트엔드"))
    frontend_done = [
        [
            "사정률 발생빈도 분석 화면",
            "완료",
            "분석 기간·분류·세부값 옵션 선택 후 빈도최대·공백·차이최대 3가지 방식의 1순위 구간을 한 화면에서 비교, 예상 투찰금액 자동 계산",
        ],
        [
            "업체 사정률 분석 화면",
            "완료",
            "발주처·예가 변동폭·기초금액 범위·업종 5종 검색 조건으로 업체 투찰 분포와 갭을 분석",
        ],
        [
            "종합 분석 화면",
            "완료",
            "세 가지 분석 방법의 1순위와 합치 정도를 한눈에 보여주고 종합 1순위 사정률·예상 투찰금액 산출, 분석 결과·투찰 리스트 엑셀 저장",
        ],
        [
            "사용자 분석 조건 저장",
            "완료",
            "마지막에 사용한 분석 조건이 다음 공고 진입 시 자동 적용",
        ],
        [
            "공고 화면 사용성 개선",
            "완료",
            "공고번호에서 원문 바로가기, 행 클릭 시 우측 요약 패널 + 본 화면 가림 방지, 한글 검색 입력 안정화, 종합분석 화면 새로고침·북마크 지원",
        ],
        [
            "서비스·관리자 영역 분리",
            "완료",
            "관리자 전용 영역 풀페이지 전환 + 사용자/수집/저장공간/오류 4개 서브 화면 분리",
        ],
        [
            "프론트엔드 자동 테스트",
            "완료",
            "주요 사용자 시나리오 18건 실제 브라우저 자동 테스트 모두 통과",
        ],
        [
            "브랜드·UI 정비",
            "완료",
            "서비스명 비드스타 통일, 아이콘·색상 토큰 정합화, 화면 폭별 4단계 반응형 적용",
        ],
    ]
    story.append(make_table(
        ["작업 항목", "상태", "2주차 결과"],
        frontend_done,
        col_widths=[42 * mm, 20 * mm, 108 * mm]
    ))

    story.append(Spacer(1, 8))

    # ── 2. 다음 주 작업 계획 ─────────────────────────
    story.append(make_section_title(2, "다음 주 작업 계획 (3주차: 05-04 ~ 05-08)"))

    next_week = [
        ["NAS 실배포", "고객 NAS 환경에 운영 환경 배포, 외부 접속 도메인·보안 인증서 연결, 자동 백업 정상 동작 확인"],
        ["UI/UX 디자인 시안 마감", "공고/분석/관리자 주요 화면 디자인 시안 확정 및 컴포넌트 가이드 정합화"],
        ["분석 신뢰도 가시화", "관리자 대시보드에 사정률 매칭률·데이터 신뢰도 지표 추가"],
        ["사정률 로직 정밀화", "공고-낙찰결과 매칭률 향상 및 분석 가중치 튜닝, 결과 신뢰도 표기"],
        ["1차 데모 전달", "2026-05-08 클라이언트 1차 데모 전달 — 주요 화면 시연 및 피드백 수렴"],
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
        ("설계 / 문서", 90, "디자인 시안 확정 잔여"),
        ("백엔드", 50, "실 데이터 연동·자동 수집·예측 로직 1차 완료. 매칭률 개선·분석 정밀화 잔여"),
        ("프론트엔드", 35, "주요 분석 화면 1차 구현 + 사용성 개선 완료. 디자인 시안 확정과 화면 마감 잔여"),
        ("배포 / 인프라", 10, "운영 환경 준비 완료. NAS 실배포·도메인·인증서 적용 잔여"),
        ("테스트", 40, "백엔드·프론트엔드 자동 테스트 110건 통과. 통합·부하·인수 시나리오 잔여"),
        ("전체", 40, "1차 기능 구현 완료, 디자인 마감·실배포·분석 정밀화 단계 진입"),
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
