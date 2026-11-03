"""
코스피200 크롤러 GUI (PyQt6)

사용법:
    pip install requests openpyxl PyQt6
    python kospi200_gui.py

실행파일(.exe) 만들기:
    build.bat  →  dist\KOSPI200Crawler.exe

데이터 수집은 kospi200_crawler.py의 함수를 그대로 사용하고,
네트워크 요청은 별도 스레드(QThread)에서 실행해 화면이 멈추지 않도록 합니다.
"""

import os
import sys
import webbrowser

import requests
from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
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
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from kospi200_crawler import (
    DAILY_COLUMNS,
    PAGE_SIZE,
    STOCK_COLUMNS,
    fetch_constituents,
    fetch_daily_prices,
    fetch_index_summary,
    save_csv,
    save_excel,
)

RISE_COLOR = "#f87171"  # 국내 증시 관례: 상승 빨강, 하락 파랑
FALL_COLOR = "#60a5fa"
STOCK_HEADERS = ["순위", *STOCK_COLUMNS.values()]
DAILY_HEADERS = list(DAILY_COLUMNS.values())
NUMERIC_KEYS = {"순위", "현재가", "전일비", "등락률(%)", "거래량", "거래대금(백만)", "시가총액(억)",
                "종가", "시가", "고가", "저가"}
CHANGE_KEYS = {"전일비", "등락률(%)"}

STYLESHEET = """
QMainWindow, QWidget#central {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #172554);
}
QWidget { color: #e2e8f0; font-size: 10pt; }
QLabel { background: transparent; }

/* 상단 배너: 지수 현재가 */
QFrame#banner {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:0.55 #4f46e5, stop:1 #7c3aed);
}
QLabel#bannerTitle { color: white; font-size: 18pt; font-weight: 800; }
QLabel#bannerSub { color: rgba(255,255,255,0.8); }
QLabel#indexValue { color: white; font-size: 26pt; font-weight: 800; }
QLabel#indexChange { font-size: 12pt; font-weight: 800; padding: 4px 12px; border-radius: 12px;
    background: white; color: #334155; }

/* 카드 */
QFrame#card { background: rgba(30, 41, 59, 0.85); border: 1px solid #334155; border-radius: 14px; }
QLabel#cardTitle { color: #93c5fd; font-weight: 700; font-size: 11pt; }

/* 입력 위젯 */
QLineEdit, QSpinBox {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 7px 12px; color: #f8fafc; selection-background-color: #4f46e5;
}
QLineEdit:focus, QSpinBox:focus { border-color: #6366f1; }
QSpinBox::up-button, QSpinBox::down-button { width: 18px; border: none; background: transparent; }

/* 버튼 */
QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white; background: #334155;
}
QPushButton:hover { background: #475569; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed); }
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6); }
QPushButton#danger { background: #e11d48; }
QPushButton#danger:hover { background: #f43f5e; }
QPushButton#excel { background: #059669; }
QPushButton#excel:hover { background: #10b981; }
QPushButton#csv { background: #0284c7; }
QPushButton#csv:hover { background: #0ea5e9; }
QPushButton:disabled, QPushButton#primary:disabled, QPushButton#danger:disabled,
QPushButton#excel:disabled, QPushButton#csv:disabled { background: #1e293b; color: #475569; }

/* 탭 */
QTabWidget::pane { border: none; }
QTabBar::tab {
    background: #1e293b; color: #94a3b8; padding: 8px 20px; margin-right: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: 700;
}
QTabBar::tab:selected { background: #4f46e5; color: white; }

/* 표 */
QTableWidget {
    background: transparent; alternate-background-color: rgba(51, 65, 85, 0.35);
    border: none; gridline-color: transparent;
    selection-background-color: rgba(99, 102, 241, 0.45); selection-color: white;
}
QTableWidget::item { padding: 4px; border-bottom: 1px solid #1e293b; }
QHeaderView::section {
    background: #1e293b; color: #93c5fd; font-weight: 700;
    padding: 8px; border: none; border-bottom: 2px solid #6366f1;
}
QTableCornerButton::section { background: #1e293b; border: none; }

/* 스크롤바 */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #475569; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #6366f1; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }

/* 진행 표시줄 */
QProgressBar {
    background: #1e293b; border: none; border-radius: 8px;
    height: 16px; text-align: center; color: white; font-weight: 700;
}
QProgressBar::chunk {
    border-radius: 8px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed);
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


def to_number(text) -> float:
    try:
        return float(str(text).replace(",", ""))
    except ValueError:
        return 0.0


def change_color(text) -> str | None:
    value = to_number(text)
    return RISE_COLOR if value > 0 else FALL_COLOR if value < 0 else None


class NumericItem(QTableWidgetItem):
    """'12,345' 같은 문자열을 숫자로 비교해 정렬하는 셀"""

    def __lt__(self, other):
        return to_number(self.text()) < to_number(other.text())


def make_table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setAlternatingRowColors(True)
    table.setShowGrid(False)
    table.setSortingEnabled(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(32)
    table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    return table


def fill_table(table: QTableWidget, rows: list[dict], order=Qt.SortOrder.AscendingOrder) -> None:
    """dict 목록을 표에 채우고, 숫자는 오른쪽 정렬·등락은 색으로 표시"""
    headers = [table.horizontalHeaderItem(c).text() for c in range(table.columnCount())]
    table.setSortingEnabled(False)  # 채우는 동안 정렬이 끼어들면 행이 뒤섞임
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        color = change_color(row.get("전일비"))
        for c, key in enumerate(headers):
            text = str(row.get(key, ""))
            if key == "기준시각":
                text = text[11:19]  # 2026-11-03T14:15:21+09:00 → 14:15:21
            if key in NUMERIC_KEYS:
                item = NumericItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            else:
                item = QTableWidgetItem(text)
            if key in CHANGE_KEYS and color:
                item.setForeground(QColor(color))
            elif key == "종목명":
                item.setFont(QFont("Malgun Gothic", 10, QFont.Weight.Bold))
            elif key in ("종목코드", "기준시각"):
                item.setForeground(QColor("#94a3b8"))
            table.setItem(r, c, item)
    table.setSortingEnabled(True)
    table.sortItems(0, order)  # 켜는 순간 첫 열 내림차순으로 정렬되므로 원하는 순서로 되돌림


class CrawlWorker(QThread):
    """백그라운드에서 지수 요약, 편입종목(페이지 단위), 일별 시세를 수집하는 스레드"""

    summary_ready = pyqtSignal(dict)
    log = pyqtSignal(str)
    done = pyqtSignal(list, list)  # (편입종목, 일별시세)
    failed = pyqtSignal(str)

    def __init__(self, limit: int, days: int):
        super().__init__()
        self.limit = limit
        self.days = days
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        try:
            self.log.emit("지수 요약 불러오는 중...")
            self.summary_ready.emit(fetch_index_summary())
            stocks = fetch_constituents(self.limit, log=lambda m: self.log.emit(m.strip()),
                                        should_stop=lambda: self._stop)
            daily = fetch_daily_prices(self.days) if self.days > 0 and not self._stop else []
        except requests.RequestException as e:
            self.failed.emit(f"데이터 요청 실패: {e}")
            return
        self.done.emit(stocks, daily)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("코스피200 크롤러")
        self.resize(1280, 860)

        self.summary: dict = {}
        self.stocks: list[dict] = []
        self.daily: list[dict] = []
        self.worker: CrawlWorker | None = None

        # --- 상단 배너: 지수 현재가 ---
        banner = QFrame()
        banner.setObjectName("banner")
        title = QLabel("📈  코스피200 크롤러")
        title.setObjectName("bannerTitle")
        self.banner_sub = QLabel("수집 시작을 누르면 지수와 편입종목 시세를 불러옵니다")
        self.banner_sub.setObjectName("bannerSub")
        self.index_value = QLabel("-")
        self.index_value.setObjectName("indexValue")
        self.index_change = QLabel("")
        self.index_change.setObjectName("indexChange")
        self.index_change.hide()

        banner_text = QVBoxLayout()
        banner_text.setSpacing(4)
        banner_text.addWidget(title)
        banner_text.addWidget(self.banner_sub)
        banner_layout = QHBoxLayout(banner)
        banner_layout.setContentsMargins(24, 18, 24, 18)
        banner_layout.addLayout(banner_text, 1)
        banner_layout.addWidget(self.index_value)
        banner_layout.addSpacing(10)
        banner_layout.addWidget(self.index_change)

        # --- 수집 조건 ---
        self.limit_spin = QSpinBox()
        self.limit_spin.setRange(0, 300)
        self.limit_spin.setSingleStep(PAGE_SIZE)
        self.limit_spin.setValue(200)
        self.limit_spin.setSpecialValueText("전체")  # 0 = API가 주는 전부
        self.days_spin = QSpinBox()
        self.days_spin.setRange(0, 365)
        self.days_spin.setValue(20)
        self.days_spin.setSpecialValueText("안 함")

        self.start_btn = QPushButton("🚀  수집 시작")
        self.start_btn.setObjectName("primary")
        self.start_btn.clicked.connect(self.start_crawl)
        self.stop_btn = QPushButton("⏹  중지")
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_crawl)
        self.csv_btn = QPushButton("📄  CSV 저장")
        self.csv_btn.setObjectName("csv")
        self.csv_btn.clicked.connect(self.save_csv_results)
        self.excel_btn = QPushButton("📊  엑셀 저장")
        self.excel_btn.setObjectName("excel")
        self.excel_btn.clicked.connect(self.save_excel_results)
        for btn in (self.start_btn, self.stop_btn, self.csv_btn, self.excel_btn):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)

        options = QWidget()
        row = QHBoxLayout(options)
        row.setContentsMargins(0, 4, 0, 0)
        row.setSpacing(10)
        row.addWidget(QLabel("편입종목"))
        row.addWidget(self.limit_spin)
        row.addWidget(QLabel("개"))
        row.addSpacing(12)
        row.addWidget(QLabel("일별 시세"))
        row.addWidget(self.days_spin)
        row.addWidget(QLabel("일"))
        row.addStretch(1)
        row.addWidget(self.start_btn)
        row.addWidget(self.stop_btn)
        row.addWidget(self.csv_btn)
        row.addWidget(self.excel_btn)

        # --- 결과 탭 ---
        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("🔍  종목명 또는 종목코드로 찾기")
        self.filter_edit.textChanged.connect(self.apply_filter)
        self.stock_table = make_table(STOCK_HEADERS)
        self.stock_table.cellDoubleClicked.connect(self.open_stock_page)
        self.stock_table.setToolTip("더블클릭하면 네이버페이 증권 종목 페이지를 엽니다")

        stock_tab = QWidget()
        stock_layout = QVBoxLayout(stock_tab)
        stock_layout.setContentsMargins(0, 8, 0, 0)
        stock_layout.addWidget(self.filter_edit)
        stock_layout.addWidget(self.stock_table)

        self.daily_table = make_table(DAILY_HEADERS)
        self.tabs = QTabWidget()
        self.tabs.addTab(stock_tab, "🏢  편입종목")
        self.tabs.addTab(self.daily_table, "📅  지수 일별 시세")

        # --- 하단 진행 상태 ---
        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setTextVisible(False)
        self.status_label = QLabel("✨ 대기 중")
        self.status_label.setObjectName("status")
        bottom = QHBoxLayout()
        bottom.addWidget(self.status_label, 1)
        bottom.addWidget(self.progress, 1)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 16)
        layout.setSpacing(14)
        layout.addWidget(banner)
        layout.addWidget(make_card("⚙  수집 조건", options))
        layout.addWidget(make_card("🗂  수집 결과", self.tabs), 1)
        layout.addLayout(bottom)

        central = QWidget()
        central.setObjectName("central")
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.set_running(False)

    # ---------- 수집 제어 ----------
    def start_crawl(self):
        if self.worker and self.worker.isRunning():
            return
        self.set_running(True)
        self.progress.setRange(0, 0)  # 전체 페이지 수를 미리 알 수 없어 움직이는 막대로 표시
        self.status_label.setText("⏳ 수집 중...")

        self.worker = CrawlWorker(self.limit_spin.value(), self.days_spin.value())
        self.worker.summary_ready.connect(self.on_summary)
        self.worker.log.connect(lambda msg: self.status_label.setText(f"⏳ {msg}"))
        self.worker.done.connect(self.on_done)
        self.worker.failed.connect(self.on_failed)
        self.worker.start()

    def stop_crawl(self):
        if self.worker:
            self.worker.stop()
            self.status_label.setText("⏹ 중지하는 중... (지금까지 받은 종목은 표시됩니다)")

    def set_running(self, running: bool):
        self.start_btn.setEnabled(not running)
        self.stop_btn.setEnabled(running)
        self.csv_btn.setEnabled(not running and bool(self.stocks))
        self.excel_btn.setEnabled(not running and bool(self.stocks))
        self.limit_spin.setEnabled(not running)
        self.days_spin.setEnabled(not running)

    # ---------- 워커 시그널 처리 ----------
    def on_summary(self, summary: dict):
        self.summary = summary
        change = summary["전일비"]
        color = {RISE_COLOR: "#dc2626", FALL_COLOR: "#1d4ed8"}.get(change_color(change), "#334155")  # 흰 배지 위라 진한 색
        sign = "▲" if to_number(change) > 0 else "▼" if to_number(change) < 0 else ""
        self.index_value.setText(summary["현재가"])
        self.index_change.setText(f"{sign} {change.lstrip('-')}  ({summary['등락률(%)']}%)")
        self.index_change.setStyleSheet(f"color: {color};")
        self.index_change.show()

        details = [f"{k} {summary[k]}" for k in ("시가", "고가", "저가", "52주 최고", "52주 최저") if k in summary]
        market = "장중" if summary["장상태"] == "OPEN" else "장마감"
        time_text = summary["기준시각"][:16].replace("T", " ")
        self.banner_sub.setText(f"{market} · {time_text} 기준   |   " + "   ".join(details))

    def on_done(self, stocks: list, daily: list):
        self.stocks, self.daily = stocks, daily
        fill_table(self.stock_table, stocks)
        fill_table(self.daily_table, daily, Qt.SortOrder.DescendingOrder)  # 최근 날짜가 위
        self.apply_filter()
        self.progress.setRange(0, 1)
        self.progress.setValue(1)
        self.set_running(False)
        stopped = " (중지됨)" if self.worker and self.worker._stop else ""
        self.status_label.setText(f"✅ 완료{stopped}: 편입종목 {len(stocks)}개, 일별 시세 {len(daily)}일")

    def on_failed(self, msg: str):
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.set_running(False)
        self.status_label.setText("❌ 수집 실패")
        QMessageBox.critical(self, "오류", msg)

    # ---------- 표 동작 ----------
    def apply_filter(self):
        keyword = self.filter_edit.text().strip().lower()
        name_col = STOCK_HEADERS.index("종목명")
        code_col = STOCK_HEADERS.index("종목코드")
        for r in range(self.stock_table.rowCount()):
            name = self.stock_table.item(r, name_col).text().lower()
            code = self.stock_table.item(r, code_col).text()
            self.stock_table.setRowHidden(r, bool(keyword) and keyword not in name and keyword not in code)

    def open_stock_page(self, row: int, _col: int):
        code = self.stock_table.item(row, STOCK_HEADERS.index("종목코드")).text()
        webbrowser.open(f"https://stock.naver.com/domestic/stock/{code}")

    # ---------- 저장 ----------
    def save_csv_results(self):
        path, _ = QFileDialog.getSaveFileName(self, "CSV 저장", "kospi200.csv", "CSV 파일 (*.csv)")
        if not path:
            return
        try:
            save_csv(path, self.stocks)
            if self.daily:
                save_csv(path.rsplit(".", 1)[0] + "_daily.csv", self.daily)
        except PermissionError:
            QMessageBox.critical(self, "오류", "파일이 다른 프로그램에서 열려 있으면 닫은 뒤 다시 저장하세요.")
            return
        except OSError as e:
            QMessageBox.critical(self, "오류", f"저장 실패: {e}")
            return
        extra = " (+ _daily.csv)" if self.daily else ""
        self.status_label.setText(f"💾 CSV 저장 완료: {path}{extra}")

    def save_excel_results(self):
        path, _ = QFileDialog.getSaveFileName(self, "엑셀 저장", "kospi200.xlsx", "엑셀 파일 (*.xlsx)")
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        sheets = {"지수요약": [self.summary], "편입종목": self.stocks}
        if self.daily:
            sheets["일별시세"] = self.daily
        try:
            save_excel(path, sheets)
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
