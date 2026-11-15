#!/usr/bin/env python3
"""Render the eight-page CarCue review proposal from fixed, audited facts.

Only real showcase03 screenshots are embedded. Visual review is a separate,
manual step; this renderer never declares visual QA passed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from PIL import Image


BLUE = colors.HexColor("#2859E8")
INK = colors.HexColor("#18233B")
MUTED = colors.HexColor("#536078")
PALE = colors.HexColor("#EEF3FF")
LINE = colors.HexColor("#DCE3F2")
W, H = A4
M = 40
CW = W - M * 2
APK_SHA = "5ef560ba1a24e3ce206aeeb6f4f336018b6e8a182bec7214aabc5dd4a261479f"
MOVIE_SHA = "638c1f54d3e29ddba3212154c118267bcfc8be21a3dda0ad004066f3e600e18d"
SOURCE_COMMIT = "07edb2ae408f8b0d6051fa49cf90af1d29c97108"
REPO = "https://github.com/calmkeen/Hyundai_appdevchallenge2026"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Proposal:
    def __init__(self, root: Path, out: Path):
        self.root, self.out = root, out
        self.assets = root / "output/qa/multilingual-session-20261115/sdk-session-showcase-20261115-03"
        self.used: dict[str, str] = {}
        out.mkdir(parents=True, exist_ok=True)
        self.pdf = out / "CarCue-first-submission-plan.pdf"
        self.c = canvas.Canvas(str(self.pdf), pagesize=A4, pageCompression=1)
        self.c.setTitle("CarCue | 1차 제출 기획서 — 검토본")
        self.c.setAuthor("CarCue")
        self.c.setSubject("실제 Pleos SDK 앱 기반 다국어 차량 이용 가이드")
        pdfmetrics.registerFont(TTFont("CarCue", "/System/Library/Fonts/Supplemental/AppleGothic.ttf"))
        self.styles = {
            "body": ParagraphStyle("body", fontName="CarCue", fontSize=10.6, leading=16.5, textColor=INK, wordWrap="CJK", alignment=TA_LEFT),
            "small": ParagraphStyle("small", fontName="CarCue", fontSize=8.5, leading=12.6, textColor=MUTED, wordWrap="CJK"),
            "caption": ParagraphStyle("caption", fontName="CarCue", fontSize=8, leading=11.5, textColor=MUTED, wordWrap="CJK"),
            "card": ParagraphStyle("card", fontName="CarCue", fontSize=10, leading=15, textColor=INK, wordWrap="CJK"),
            "white": ParagraphStyle("white", fontName="CarCue", fontSize=11, leading=17, textColor=colors.white, wordWrap="CJK"),
            "hash": ParagraphStyle("hash", fontName="Courier", fontSize=7.7, leading=11, textColor=MUTED, splitLongWords=True),
        }
        self.page = 0

    def p(self, text: str, x: float, top: float, width: float = CW, style: str = "body") -> float:
        para = Paragraph(text, self.styles[style])
        _, height = para.wrap(width, 1000)
        if top + height > H - 48:
            raise ValueError(f"page {self.page}: text overflows at {top + height:.1f}: {text[:70]}")
        para.drawOn(self.c, x, H - top - height)
        return top + height

    def text(self, text: str, x: float, top: float, size: float = 12, color=INK, font="CarCue"):
        self.c.setFont(font, size)
        self.c.setFillColor(color)
        self.c.drawString(x, H - top - size, text)

    def rect(self, x: float, top: float, width: float, height: float, fill=PALE, radius: float = 10, stroke=None):
        self.c.setFillColor(fill)
        self.c.setStrokeColor(stroke or fill)
        self.c.roundRect(x, H - top - height, width, height, radius, fill=1, stroke=bool(stroke))

    def image(self, name: str, x: float, top: float, width: float, max_height: float | None = None):
        path = self.assets / name
        self.used[name] = sha(path)
        with Image.open(path) as im:
            iw, ih = im.size
        height = width * ih / iw
        if max_height is not None and height > max_height:
            width, height = max_height * iw / ih, max_height
        self.c.drawImage(str(path), x, H - top - height, width, height, preserveAspectRatio=True, mask="auto")
        return height

    def header(self, no: int, eyebrow: str, title: str, subtitle: str):
        self.page = no
        self.c.setFillColor(colors.white)
        self.c.rect(0, 0, W, H, fill=1, stroke=0)
        self.text("CarCue", M, 23, 11, BLUE, "Helvetica-Bold")
        self.text(eyebrow, M, 64, 9, BLUE)
        self.text(title, M, 85, 25, INK)
        self.p(subtitle, M, 125, CW, "small")
        self.c.setStrokeColor(LINE)
        self.c.line(M, 40, W - M, 40)
        self.text("1차 제출 기획서 · 검토본  |  2026.11.15", M, H - 30, 7.5, MUTED)
        self.text(f"{no:02d} / 08", W - 75, H - 30, 7.5, MUTED, "Helvetica")

    def section(self, label: str, top: float, text: str, x=M, width=CW):
        self.text(label, x, top, 12.5, BLUE)
        return self.p(text, x, top + 24, width)

    def card(self, x, top, width, height, label, text):
        self.rect(x, top, width, height)
        self.text(label, x + 14, top + 12, 12, BLUE)
        self.p(text, x + 14, top + 38, width - 28, "card")

    def finish_page(self):
        self.c.showPage()

    def cover(self):
        self.header(1, "차량이 바뀌어도 익숙한 이용 흐름", "CarCue", "실제 Pleos SDK 앱 기반 다국어 차량 이용 가이드")
        self.text("언제, 어디서든,", M, 169, 28, BLUE)
        self.text("평소와 같은 경험을.", M, 207, 28, BLUE)
        self.p("낯선 차량의 상태와 공식 안내를 내 언어로 확인하고,<br/>필요한 질문부터 이용 종료까지 같은 흐름으로 이어 갑니다.", M, 258, CW)
        self.rect(M - 1, 313, CW + 2, 292, colors.white, 8, LINE)
        self.image("door-open-physical.png", M, 314, CW)
        self.p("실제 SDK showcase03 물리 화면 · 앱의 문 열림 시각화. 전용 AVD 시험이며 실차/VIN 인증이 아닙니다.", M, 611, CW, "caption")
        widths = (CW - 20) / 3
        for i, (label, body) in enumerate([
            ("1개 안내 × 3언어", "2024 KR IONIQ 5<br/>문 안내 · 두 단계"),
            ("실제 SDK 읽기", "앞좌석 왼쪽 문<br/>열림·닫힘 수신"),
            ("무료 로컬 AI", "검수 항목 선택<br/>저장된 안내·번역")]):
            self.card(M + i * (widths + 10), 654, widths, 106, label, body)
        self.finish_page()

    def problem(self):
        self.header(2, "01 · 문제와 이용자", "설명은 들었지만, 다시 확인할 때", "렌터카·공유 차량과 외국어 이용자를 초기 대상으로 제안합니다.")
        self.p("처음 타는 차에서는 필요한 순간 조작과 상태의 의미를 다시 찾아야 합니다. 익숙하지 않은 언어는 매뉴얼 탐색과 질문을 더 어렵게 할 수 있습니다.", M, 165, CW)
        self.card(M, 230, 247, 113, "이용자에게", "자기 언어로 상태를 확인하고<br/>해당 차량의 원문 근거까지 찾는 흐름")
        self.card(M + 261, 230, 254, 113, "운영자에게", "반복 안내와 의사소통 부담을<br/>줄일 수 있는 접점")
        self.text("차량을 바꿔도 네 단계는 같게", M, 375, 15, BLUE)
        steps = [("01", "프로필·언어 선택"), ("02", "상태·공식 안내"), ("03", "질문·저장 번역"), ("04", "원문·지원·종료")]
        for i, (num, title) in enumerate(steps):
            x = M + i * 130
            self.rect(x, 412, 122, 67, colors.HexColor("#F6F8FC"), 7)
            self.text(num, x + 10, 422, 10, BLUE, "Helvetica-Bold")
            self.text(title, x + 10, 447, 10)
        self.image("language-ko.png", M + 274, 512, 241)
        self.section("지금 시연하는 언어", 517, "한국어 · English · 日本語<br/><br/>앱 UI 번역은 초안입니다. 메뉴의 다른 준비 중 언어는 현재 지원 수에 포함하지 않습니다.", width=247)
        self.p("문제와 효과는 검증할 가설입니다. 시간 절감·만족도·시장 규모는 측정하지 않았으며, 제휴나 기본 탑재를 확보한 상태도 아닙니다.", M, 720, CW, "small")
        self.finish_page()

    def sdk(self):
        self.header(3, "02 · 실제 SDK 연결", "문 상태가 바뀌면, 그림도 함께", "앱은 SDK를 읽습니다. 상태 변경은 전용 AVD의 외부 Console에서 수행합니다.")
        col = (CW - 20) / 3
        for i, (name, label) in enumerate([
            ("car-initial-closed.png", "CLOSED · 최초 닫힘"),
            ("car-callback-open.png", "OPEN · 콜백 열림"),
            ("car-restored-closed.png", "CLOSED · 다시 닫힘")]):
            x = M + i * (col + 10)
            self.rect(x, 171, col, 110, colors.HexColor("#F7F9FC"), 7)
            self.image(name, x + 5, 185, col - 10)
            self.text(label, x + 9, 259, 8.5, BLUE)
        self.p("앞좌석 왼쪽 문(ROW_1_LEFT)의 실제 수신 값을 사전 렌더 프레임에 반영했습니다. 실시간 3D 모델이나 문 제어 기능이 아니며 앱의 SDK SET 호출은 없습니다.", M, 301, CW)
        self.image("official-guide-step2.png", M, 365, 360)
        self.section("근거를 함께", 374, "선택 프로필<br/>공식 매뉴얼 판본<br/>원문 출처<br/>두 단계 안내", x=416, width=139)
        self.p("현재 공식 안내: 2024 KR IONIQ 5 문 가이드 1개 × 3언어. 공식 원문 기반 자체 요약·AI 보조 의미 대조이며 OEM 승인이나 인간 전문가 검수 자료는 아닙니다.", M, 645, CW, "small")
        self.rect(M, 707, CW, 57)
        self.p("문 상태만으로 잠금·고장·운행 가능 여부를 판정하지 않습니다.<br/>안전벨트는 안내 이미지이며 착용 센서에는 연결하지 않았습니다.", M + 13, 718, CW - 26, "small")
        self.finish_page()

    def ai(self):
        self.header(4, "03 · 다국어 질문과 번역", "AI는 고르고, 등록된 안내를 전달", "유료 AI 자동 전환 없이 무료 로컬 Ollama/qwen3:4b를 실제 호출했습니다.")
        self.card(M, 168, CW, 101, "답변은 검수된 문자열로 구성", "모델의 역할은 등록된 항목 선택입니다. 서버가 프로필·판본·단위·출처를 검사한 뒤 본문·두 단계·모든 주의문을 조립합니다. 자유 생성 고장 진단을 제공하지 않습니다.")
        self.image("ask-ko.png", M, 294, 247)
        self.image("translation-en.png", M + 268, 294, 247)
        self.p("한국어 ASK · 실제 무료 모델 항목 선택", M, 480, 247, "caption")
        self.p("영어 ANSWER 번역 · 저장된 검수 문구", M + 268, 480, 247, "caption")
        self.section("서로 다른 두 경로", 520, "질문: 실제 무료 모델 호출 → 검수 항목 선택 → 등록된 안내 조립<br/>ANSWER/GUIDE 번역: 같은 판본의 저장된 검수 번역 → 추가 모델 호출 0")
        self.p("같은 APK·앱 프로세스에서 한국어·영어·일본어 ASK 3회와 저장 ANSWER 번역 3회를 수행했습니다. GUIDE 저장 번역의 별도 검증 기록도 보존합니다.", M, 624, CW)
        self.rect(M, 710, CW, 54, colors.HexColor("#F6F8FC"))
        self.p("자유 QUESTION 생성 번역은 의미 오류 확인 후 기본 보류했습니다.<br/>원문 언어·대상 언어·검수 상태를 구분하고, 오래된 번역을 새 결과처럼 표시하지 않습니다.", M + 13, 719, CW - 26, "small")
        self.finish_page()

    def boundaries(self):
        self.header(5, "04 · 주행과 개인정보 경계", "쓸 수 있는 순간과 끝내는 순간", "Car UX의 실제 제한 값을 이용하며, 기어·속도만으로 앱이 주행 제한을 추론하지 않습니다.")
        self.image("drive-restricted.png", M, 172, 247)
        self.image("end-session.png", M + 268, 172, 247)
        self.p("실제 Drive 제한 화면", M, 358, 247, "caption")
        self.p("정상 이용 종료 뒤 새 이용자 초기 화면", M + 268, 358, 247, "caption")
        self.card(M, 399, 247, 127, "전송 전 동의", "질문과 전송 맥락을 확인합니다. 입력·언어·페이지 등 맥락이 바뀌면 동의를 다시 확인합니다.")
        self.card(M + 268, 399, 247, 127, "종료와 삭제 복구", "질문·결과·선택 언어를 초기화합니다. 삭제 대기는 재시도하며 공용 검수 자료는 유지합니다.")
        self.section("확인한 범위", 560, "기본 시연의 Drive → Park 복귀와 정상 이용 종료를 확인했습니다. 종료 뒤 서버 sessions/results/history는 0/0/0입니다.")
        self.rect(M, 659, CW, 107, PALE)
        self.text("추가 경계 시험은 미완료", M + 14, 672, 12, BLUE)
        self.p("실제 모델 요청 진행 중 언어 변경·Drive·이용 종료의 세 기기 시험은 전체 통과하지 못했습니다. 종료 case는 미실행입니다. 단위 검사와 실제 기기 통과를 구분합니다.", M + 14, 698, CW - 28, "card")
        self.finish_page()

    def architecture(self):
        self.header(6, "05 · 개발 구조", "상태, 근거, 공급자를 나누는 구조", "Android MVVM + 단방향 상태 흐름(UDF), 서버 모듈형 구조로 현재 규모에 맞춰 개발합니다.")
        boxes = [
            (M, 176, 158, 78, "Compose UI", "화면 · 이벤트 · 언어"),
            (M + 178, 176, 158, 78, "ViewModel", "StateFlow · 정책 · 동의"),
            (M + 356, 176, 159, 78, "Repository", "SDK · 콘텐츠 · API 경계"),
            (M, 302, 247, 80, "Pleos / Mock", "별도 어댑터 · Source 표시"),
            (M + 268, 302, 247, 80, "FastAPI", "등록 자료 · 세션 · 요청 검증"),
        ]
        for x, top, width, height, label, body in boxes:
            self.card(x, top, width, height, label, body)
        self.c.setStrokeColor(BLUE)
        for x in (M + 163, M + 341):
            self.c.line(x, H - 215, x + 10, H - 215)
        self.c.line(M + 435, H - 260, M + 435, H - 294)
        for i, (label, detail) in enumerate([
            ("Catalog", "프로필 · 판본 · 검수 번역"),
            ("SQLite", "세션 · 결과 · 삭제"),
            ("Ollama", "무료 로컬 항목 선택")]):
            x = M + i * 176
            self.rect(x, 416, 163, 67, colors.HexColor("#F6F8FC"), 7)
            self.text(label, x + 12, 427, 11, BLUE, "Helvetica-Bold")
            self.p(detail, x + 12, 451, 139, "caption")
        self.section("현재의 모듈 경계", 518, "Android 단일 Gradle 모듈과 단일 서버 배포를 유지합니다. 순수 정책과 I/O 구현은 점진적으로 분리하고, AI 공급자와 검수 단위·출처 검증을 독립시킵니다.")
        self.section("검증과 이력", 624, "Git flow의 develop + 작업별 feature 브랜치에서 검증·커밋을 남깁니다. 계약·UI 자원·콘텐츠·백엔드 회귀와 Android Demo JVM/APK CI를 실제 SDK AVD·모델 시험과 구분합니다.")
        self.p("새 HTTP 429 기능은 후속 개발본이며 이번 제출 검증 APK에는 포함되지 않습니다. Demo CI 산출물은 Mock이며 Pleos 런타임 검증을 대신하지 않습니다.", M, 738, CW, "small")
        self.finish_page()

    def roadmap(self):
        self.header(7, "06 · 단계별 확장", "먼저 한 안내를 정확하게", "현재 구현, 다음 검증, 장기 비전을 나눕니다. 범위를 넓히기 전에 근거와 언어 품질을 확보합니다.")
        self.card(M, 174, CW, 133, "NOW · 이번 제출", "2024 KR IONIQ 5 · 문 가이드 1개 · 두 단계 · 3언어<br/>실제 Pleos SDK 문 값과 시각화, 무료 항목 선택, 저장 번역<br/>기본 Drive/Park UX · 정상 종료 · 공식 원문/지원 연결")
        self.card(M, 329, CW, 133, "NEXT · 별도 검증", "세 진행 중 응답 경계의 기기 시험 완결<br/>개발본 429 처리의 별도 APK 검증<br/>자동 빌드·제출물 재현성 및 사용자 평가 강화")
        self.card(M, 484, CW, 133, "PLAN · 확장 비전", "충전 · 시트/미러 · 표시등의 추가 3주제 × 3언어 = 9개 안내<br/>50개국 이용 환경 지원<br/>공식 자료·이용 권한·차량별 SDK 지원·언어별 검수를 거쳐 확대")
        self.section("효과 측정도 다음 단계", 650, "같은 과제로 안내 찾기 성공률, 이해 오류, 소요 시간, 도움 요청의 명확성을 비교할 예정입니다. 현재 절감 효과나 만족도를 측정한 결과는 없습니다.")
        self.p("계획 수치를 현재 구현·연결·검수 완료 수치로 사용하지 않습니다.", M, 754, CW, "small")
        self.finish_page()

    def evidence(self):
        self.header(8, "07 · 제출 구성과 근거", "검증된 제품과 개발 이력을 함께", "검토용 기획서입니다. 기존 APK·영상·기획 원본은 보존하며 최종 제출 배치나 전송은 수행하지 않습니다.")
        self.text("01  Android APK", M, 169, 14, BLUE, "Helvetica-Bold")
        self.p("carcue-pleos-session-boundaries-debug.apk", M, 197, CW, "small")
        self.p(APK_SHA[:32] + "<br/>" + APK_SHA[32:], M, 217, CW, "hash")
        self.text("02  34초 소개 영상", M, 263, 14, BLUE)
        self.p("carcue-sdk-live-intro.mp4 · 기능별 약 2초 · 실제 언어 선택 전환 · 기존 무료 BGM", M, 291, CW, "small")
        self.p(MOVIE_SHA[:32] + "<br/>" + MOVIE_SHA[32:], M, 313, CW, "hash")
        self.text("03  소스와 검증 기록", M, 359, 14, BLUE)
        product_url = REPO + "/tree/" + SOURCE_COMMIT
        self.p(f'<link href="{product_url}" color="#2859E8">검증 제품 기준 소스 · 07edb2ae</link><br/><link href="{REPO}/tree/develop" color="#2859E8">추가 개발 이력 · develop</link> (검증 APK와 차이가 있을 수 있음)', M, 387, CW, "small")
        self.p(SOURCE_COMMIT, M, 426, CW, "hash")
        self.rect(M, 463, CW, 116)
        self.text("실제 기본 시연 PASS · 194.754초", M + 14, 477, 13, BLUE)
        self.p("SDK showcase03: 같은 APK·프로세스의 문 개폐, 실제 ASK 3회와 저장 ANSWER 번역 3회, 일반 Drive/Park와 정상 종료를 확인했습니다. 34초 영상은 이 실제 앱 원본을 편집한 소개본입니다.", M + 14, 507, CW - 28, "card")
        self.p("실차/VIN · 벨트 센서 · 차량 제어는 검증 범위가 아닙니다. 진행 중 세 응답 경계는 미완료이며 종료 case는 미실행입니다. 자유 QUESTION 번역과 유료 AI는 보류합니다.", M, 601, CW, "small")
        self.p("출처·권리: 차량/벨트는 사용자 지정 Pleos 녹화 프레임입니다. 그래픽의 외부 재배포 권한은 미확인이며 음악의 CC BY 조건을 그래픽에 적용하지 않습니다.", M, 661, CW, "small")
        self.p("근거: SDK_SESSION_VALIDATION · SDK_LIVE_INTRO · AI_CAUTION_VALIDATION · LOCAL_AI_INTEGRATION · ARCHITECTURE · CI · PLEOS_VISUAL_SOURCE<br/>PDF 화면은 SDK showcase03 실제 캡처만 사용했습니다.", M, 718, CW, "caption")
        self.finish_page()

    def build(self):
        for method in (self.cover, self.problem, self.sdk, self.ai, self.boundaries, self.architecture, self.roadmap, self.evidence):
            method()
        self.c.save()
        manifest = {
            "pdf": str(self.pdf), "pdf_sha256": sha(self.pdf), "page_count": 8,
            "visual_review": "PENDING", "source_capture_directory": str(self.assets),
            "assets_sha256": self.used, "slogan": "언제, 어디서든, 평소와 같은 경험을.",
            "verified_product_commit": SOURCE_COMMIT, "apk_sha256": APK_SHA, "movie_sha256": MOVIE_SHA,
        }
        (self.out / "proposal-source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"pdf": str(self.pdf), "sha256": manifest["pdf_sha256"], "pages": 8}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=Path("/Users/younsung/hyundai"))
    parser.add_argument("--output-dir", type=Path, default=Path("/Users/younsung/hyundai/output/pdf/20261115"))
    args = parser.parse_args()
    Proposal(args.workspace_root.resolve(), args.output_dir.resolve()).build()


if __name__ == "__main__":
    main()
