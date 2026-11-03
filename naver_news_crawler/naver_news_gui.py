"""
네이버 뉴스 크롤러 GUI (PyQt6)

사용법:
    pip install requests beautifulsoup4 openpyxl PyQt6
    python naver_news_gui.py

실행파일(.exe) 만들기:
    build.bat  →  dist\\NaverNewsCrawler.exe

크롤링 로직은 naver_news_crawler.py의 함수를 그대로 사용하고,
네트워크 요청은 별도 스레드(QThread)에서 실행해 화면이 멈추지 않도록 합니다.
"""

import html
import os
import sys
import time
from urllib.parse import urlencode

import requests
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from naver_news_crawler import (
    get_soup,
    parse_generic_article,
    parse_naver_article,
    parse_search_results,
    save_csv,
    save_excel,
)


STYLESHEET = """
QMainWindow, QWidget#central {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #1e1b4b);
}
QWidget { color: #e2e8f0; font-size: 10pt; }

/* 상단 배너 */
QFrame#banner {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6366f1, stop:0.5 #a855f7, stop:1 #ec4899);
}
QLabel#bannerTitle { color: white; font-size: 20pt; font-weight: 800; background: transparent; }
QLabel#bannerSub { color: rgba(255,255,255,0.85); font-size: 10pt; background: transparent; }
QLabel#countBadge {
    color: white; font-weight: 700; padding: 6px 14px; border-radius: 14px;
    background: rgba(255,255,255,0.22);
}

/* 카드 */
QFrame#card {
    background: rgba(30, 41, 59, 0.85);
    border: 1px solid #334155;
    border-radius: 14px;
}
QLabel { background: transparent; }
QLabel#cardTitle { color: #c4b5fd; font-weight: 700; font-size: 11pt; }

/* 입력 위젯 */
QLineEdit, QSpinBox {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 7px 12px; color: #f8fafc; selection-background-color: #a855f7;
}
QLineEdit:focus, QSpinBox:focus { border-color: #a855f7; }
QSpinBox::up-button, QSpinBox::down-button { width: 18px; border: none; background: transparent; }
QCheckBox { spacing: 8px; }
QCheckBox::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 2px solid #64748b; background: #0f172a;
}
QCheckBox::indicator:checked {
    border-color: #ec4899;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #a855f7, stop:1 #ec4899);
}

/* 버튼 */
QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white; background: #334155;
}
QPushButton:hover { background: #475569; }
QPushButton:disabled { background: #1e293b; color: #475569; }
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #ec4899);
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818cf8, stop:1 #f472b6);
}
QPushButton#danger { background: #e11d48; }
QPushButton#danger:hover { background: #f43f5e; }
QPushButton#excel { background: #059669; }
QPushButton#excel:hover { background: #10b981; }
QPushButton#csv { background: #0284c7; }
QPushButton#csv:hover { background: #0ea5e9; }
QPushButton#primary:disabled, QPushButton#danger:disabled,
QPushButton#excel:disabled, QPushButton#csv:disabled { background: #1e293b; color: #475569; }

/* 표 */
QTableWidget {
    background: transparent; alternate-background-color: rgba(51, 65, 85, 0.35);
    border: none; gridline-color: transparent;
    selection-background-color: rgba(168, 85, 247, 0.45); selection-color: white;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #1e293b; }
QHeaderView::section {
    background: #1e293b; color: #c4b5fd; font-weight: 700;
    padding: 8px; border: none; border-bottom: 2px solid #a855f7;
}
QTableCornerButton::section { background: #1e293b; border: none; }

/* 본문 뷰어 */
QTextBrowser { background: transparent; border: none; }

/* 스크롤바 */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #475569; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #a855f7; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

QSplitter::handle { background: transparent; height: 10px; }

/* 진행 표시줄 */
QProgressBar {
    background: #1e293b; border: none; border-radius: 8px;
    height: 16px; text-align: center; color: white; font-weight: 700;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:0.5 #a855f7, stop:1 #ec4899);
}
QLabel#status { color: #94a3b8; }
"""


def resource_path(name: str) -> str:
    """PyInstaller 실행파일에서는 임시 압축 해제 폴더(sys._MEIPASS), 평소에는 이 파일의 폴더 기준 경로"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def make_card(title: str, widget: QWidget) -> QFrame:
    """제목이 있는 둥근 카드 안에 위젯을 넣고, 은은한 그림자를 적용"""
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 12, 16, 12)
    label = QLabel(title)
    label.setObjectName("cardTitle")
    layout.addWidget(label)
    layout.addWidget(widget)

    shadow = QGraphicsDropShadowEffect(blurRadius=24, xOffset=0, yOffset=4)
    shadow.setColor(QColor(0, 0, 0, 120))
    card.setGraphicsEffect(shadow)
    return card


def build_search_url(query: str, news_tab: bool) -> str:
    """검색어로 네이버 통합검색(nexearch) 또는 뉴스 탭(news) URL 생성"""
    if news_tab:
        params = {"where": "news", "query": query}
    else:
        params = {"where": "nexearch", "sm": "top_hty", "fbm": "0", "ie": "utf8", "query": query}
    return "https://search.naver.com/search.naver?" + urlencode(params)


class CrawlWorker(QThread):
    """백그라운드에서 검색 결과와 기사 본문을 수집하는 스레드"""

    found = pyqtSignal(int)              # 검색 결과에서 찾은 기사 수
    article_done = pyqtSignal(int, dict)  # (순번, 기사 정보)
    failed = pyqtSignal(str)
    finished_all = pyqtSignal()

    def __init__(self, url: str, limit: int, delay: float):
        super().__init__()
        self.url = url
        self.limit = limit
        self.delay = delay
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            articles = parse_search_results(get_soup(self.url))[: self.limit]
        except requests.RequestException as e:
            self.failed.emit(f"검색 페이지 요청 실패: {e}")
            self.finished_all.emit()
            return

        self.found.emit(len(articles))

        for i, article in enumerate(articles):
            if self._stop:
                break
            try:
                if article["naver_url"]:
                    detail = parse_naver_article(article["naver_url"])
                else:
                    detail = parse_generic_article(article["url"])
            except requests.RequestException:
                detail = {"title": "", "press": "", "date": "", "content": ""}

            article["title"] = detail["title"] or article["title"]
            article["press"] = detail["press"]
            article["date"] = detail["date"]
            article["content"] = detail["content"] or article["summary"]

            self.article_done.emit(i, article)
            time.sleep(self.delay)  # 서버 부하를 줄이기 위한 요청 간격

        self.finished_all.emit()


class MainWindow(QMainWindow):
    COLUMNS = ["제목", "언론사", "날짜"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1280, 900)

        self.articles: list[dict] = []
        self.worker: CrawlWorker | None = None

        # --- 상단 검색 조건 ---
        self.query_edit = QLineEdit("반도체")
        self.query_edit.setPlaceholderText("검색어를 입력하세요")
        self.query_edit.setMinimumWidth(220)
        self.query_edit.returnPressed.connect(self.start_crawl)

        self.news_check = QCheckBox("뉴스 탭에서 수집 (더 많은 기사)")

        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(1, 100)
        self.limit_spin.setValue(10)

        self.start_btn = QPushButton("🚀  크롤링 시작")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_crawl)

        self.stop_btn = QPushButton("⏹  중지")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_crawl)

        self.save_btn = QPushButton("📄  CSV 저장")
        self.save_btn.setObjectName("csv")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_results)

        self.excel_btn = QPushButton("📊  엑셀 저장")
        self.excel_btn.setObjectName("excel")
        self.excel_btn.setEnabled(False)
        self.excel_btn.clicked.connect(self.save_excel_results)

        for btn in (self.start_btn, self.stop_btn, self.save_btn, self.excel_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        # --- 상단 배너 ---
        banner = QFrame()
        banner.setObjectName("banner")
        title = QLabel("📰  네이버 뉴스 크롤러")
        title.setObjectName("bannerTitle")
        subtitle = QLabel("검색어로 최신 기사를 모아 본문까지 한눈에 확인하고, CSV·엑셀로 저장하세요")
        subtitle.setObjectName("bannerSub")
        self.count_badge = QLabel("수집 0건")
        self.count_badge.setObjectName("countBadge")

        banner_text = QVBoxLayout()
        banner_text.setSpacing(2)
        banner_text.addWidget(title)
        banner_text.addWidget(subtitle)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 18, 24, 18)
        banner_layout.addLayout(banner_text, 1)
        banner_layout.addWidget(self.count_badge)

        # --- 검색 조건 카드 ---
        search_row = QWidget()
        top = QHBoxLayout(search_row)
        top.setContentsMargins(0, 4, 0, 0)
        top.setSpacing(10)
        top.addWidget(QLabel("🔍"))
        top.addWidget(self.query_edit, 1)
        top.addWidget(self.news_check)
        top.addWidget(QLabel("최대"))
        top.addWidget(self.limit_spin)
        top.addWidget(QLabel("건"))
        top.addSpacing(8)
        top.addWidget(self.start_btn)
        top.addWidget(self.stop_btn)
        top.addWidget(self.save_btn)
        top.addWidget(self.excel_btn)

        # --- 기사 목록 표 ---
        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.itemSelectionChanged.connect(self.show_article)

        # --- 기사 본문 보기 ---
        self.viewer = QTextBrowser()
        self.viewer.setOpenExternalLinks(True)
        self.viewer.setPlaceholderText("목록에서 기사를 선택하면 본문이 표시됩니다.")

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.addWidget(make_card("🗂  기사 목록", self.table))
        splitter.addWidget(make_card("📖  기사 본문", self.viewer))
        splitter.setSizes([330, 370])

        # --- 하단 진행 상태 ---
        self.progress = QProgressBar()
        self.progress.setFormat("%p%")
        self.status_label = QLabel("✨ 대기 중")
        self.status_label.setObjectName("status")
        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(make_card("⚙  검색 조건", search_row))
        layout.addWidget(splitter, 1)
        layout.addLayout(bottom)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)

    # ---------- 크롤링 제어 ----------
    def start_crawl(self):
        query = self.query_edit.text().strip()
        if not query:
            QMessageBox.warning(self, "알림", "검색어를 입력하세요.")
            return
        if self.worker and self.worker.isRunning():
            return

        self.articles = []
        self.table.setRowCount(0)
        self.viewer.clear()
        self.progress.setValue(0)
        self.count_badge.setText("수집 0건")
        self.set_running(True)
        self.status_label.setText("⏳ 검색 결과 불러오는 중...")

        url = build_search_url(query, self.news_check.isChecked())
        self.worker = CrawlWorker(url, self.limit_spin.value(), delay=0.5)
        self.worker.found.connect(self.on_found)
        self.worker.article_done.connect(self.on_article_done)
        self.worker.failed.connect(lambda msg: QMessageBox.critical(self, "오류", msg))
        self.worker.finished_all.connect(self.on_finished)
        self.worker.start()

    def stop_crawl(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText("⏹ 중지하는 중...")

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.save_btn.setEnabled(not running and bool(self.articles))
        self.excel_btn.setEnabled(not running and bool(self.articles))

    # ---------- 워커 시그널 처리 ----------
    def on_found(self, count: int):
        self.progress.setMaximum(max(count, 1))
        self.status_label.setText(f"🔎 기사 {count}건 발견, 본문 수집 중...")
        if count == 0:
            self.status_label.setText("⚠ 검색 결과에서 기사를 찾지 못했습니다.")

    def on_article_done(self, index: int, article: dict):
        self.articles.append(article)
        row = self.table.rowCount()
        self.table.insertRow(row)
        for col, key in enumerate(["title", "press", "date"]):
            item = QTableWidgetItem(article[key])
            if key == "press":
                item.setForeground(QColor("#f9a8d4"))
            elif key == "date":
                item.setForeground(QColor("#94a3b8"))
            self.table.setItem(row, col, item)
        self.progress.setValue(index + 1)
        self.count_badge.setText(f"수집 {len(self.articles)}건")
        if row == 0:
            self.table.selectRow(0)

    def on_finished(self):
        self.set_running(False)
        self.status_label.setText(f"✅ 완료: 기사 {len(self.articles)}건 수집")

    # ---------- 본문 표시 / 저장 ----------
    def show_article(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        a = self.articles[rows[0].row()]
        link = a["naver_url"] or a["url"]
        title = html.escape(a["title"])
        paragraphs = "".join(
            f"<p style='margin:0 0 10px 0; line-height:170%; color:#e2e8f0'>{html.escape(line)}</p>"
            for line in a["content"].split("\n") if line.strip()
        )
        self.viewer.setHtml(
            f"<h2 style='color:#f8fafc; margin-bottom:6px'>{title}</h2>"
            f"<p style='margin-top:0'>"
            f"<span style='background:#ec4899; color:white; font-weight:bold'>&nbsp;{html.escape(a['press'])}&nbsp;</span>"
            f"&nbsp;&nbsp;<span style='color:#94a3b8'>🕒 {a['date']}</span><br>"
            f"<a href='{html.escape(link)}' style='color:#a5b4fc'>🔗 {html.escape(link)}</a></p>"
            f"<hr style='border:none; height:2px; background:#a855f7'>"
            f"{paragraphs}"
        )

    def save_results(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", "naver_news.csv", "CSV 파일 (*.csv)")
        if not path:
            return
        try:
            save_csv(self.articles, path)
        except OSError as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
            return
        self.status_label.setText(f"💾 CSV 저장 완료: {path}")

    def save_excel_results(self):
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", "naver_news.xlsx", "엑셀 파일 (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            save_excel(self.articles, path)
        except PermissionError:
            QMessageBox.critical(self, "오류", "파일이 엑셀에서 열려 있으면 닫은 뒤 다시 저장하세요.")
            return
        except OSError as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
            return
        self.status_label.setText(f"💾 엑셀 저장 완료: {path}")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # 스타일시트가 OS 테마와 섞이지 않도록 Fusion 기반 사용
    app.setFont(QFont("Malgun Gothic", 10))
    app.setStyleSheet(STYLESHEET)
    if os.path.exists(resource_path("app.ico")):
        app.setWindowIcon(QIcon(resource_path("app.ico")))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
