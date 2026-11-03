"""
S&P 500 데이터 분석 GUI (PyQt6)

사용법:
    pip install pandas matplotlib PyQt6
    python sp500_gui.py

CSV 불러오기 -> 클렌징 -> 선택 기간 다각도 분석 -> 그래프/표/리포트 확인 -> 결과 저장.
분석과 그래프는 sp500_analysis.py의 함수를 그대로 사용한다.
"""

import sys
from pathlib import Path

import matplotlib.dates as mdates
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QColor, QFont, QIcon
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDateEdit,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import sp500_analysis as sa

THEME = sa.THEMES["dark"]
RISE_COLOR, FALL_COLOR = THEME["blue"], THEME["orange"]  # 그래프와 같은 색: 상승 파랑, 하락 주황
DEFAULT_START, DEFAULT_END = QDate(2000, 1, 1), QDate(2019, 12, 31)

STYLESHEET = """
QMainWindow, QWidget#central {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0f172a, stop:1 #172554);
}
QWidget { color: #e2e8f0; font-size: 10pt; }
QLabel { background: transparent; }

QFrame#banner {
    border-radius: 16px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #1d4ed8, stop:0.55 #4f46e5, stop:1 #7c3aed);
}
QLabel#bannerTitle { color: white; font-size: 18pt; font-weight: 800; }
QLabel#bannerSub { color: rgba(255,255,255,0.8); }

QFrame#card { background: rgba(30, 41, 59, 0.85); border: 1px solid #334155; border-radius: 14px; }
QLabel#kpiTitle { color: #93c5fd; font-size: 9pt; font-weight: 700; }
QLabel#kpiValue { color: #f8fafc; font-size: 15pt; font-weight: 800; }

QLineEdit, QDateEdit {
    background: #0f172a; border: 2px solid #334155; border-radius: 10px;
    padding: 7px 12px; color: #f8fafc; selection-background-color: #4f46e5;
}
QLineEdit:focus, QDateEdit:focus { border-color: #6366f1; }
QDateEdit::drop-down { border: none; width: 22px; }

QPushButton {
    border: none; border-radius: 10px; padding: 9px 18px;
    font-weight: 700; color: white; background: #334155;
}
QPushButton:hover { background: #475569; }
QPushButton:disabled { color: #64748b; background: #1e293b; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #7c3aed); }
QPushButton#primary:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6); }

QTabWidget::pane { border: 1px solid #334155; border-radius: 12px; background: #1e293b; top: -1px; }
QTabBar::tab {
    background: transparent; color: #94a3b8; padding: 9px 18px; margin-right: 4px;
    border-top-left-radius: 10px; border-top-right-radius: 10px; font-weight: 700;
}
QTabBar::tab:selected { background: #1e293b; color: #f8fafc; border: 1px solid #334155; border-bottom: none; }
QTabBar::tab:hover:!selected { color: #e2e8f0; }

QTableWidget {
    background: #1e293b; alternate-background-color: #233147; border: none;
    gridline-color: #334155; selection-background-color: #4f46e5;
}
QHeaderView::section {
    background: #0f172a; color: #93c5fd; padding: 6px; border: none;
    border-bottom: 1px solid #334155; font-weight: 700;
}
QTableCornerButton::section { background: #0f172a; border: none; }
QPlainTextEdit { background: #0f172a; border: none; color: #e2e8f0; }
QScrollArea { border: none; background: transparent; }
QLabel#status { color: #94a3b8; }
"""


def resource_path(name: str) -> Path:
    """PyInstaller 실행파일에서는 임시 압축 해제 폴더(sys._MEIPASS), 평소에는 이 파일의 폴더 기준 경로"""
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)) / name


def default_save_dir() -> Path:
    """실행파일이면 exe 옆 폴더, 스크립트면 output/ (exe의 __file__은 임시 폴더라 쓰면 안 됨)"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return sa.OUT_DIR


class NumericItem(QTableWidgetItem):
    """표시는 서식 문자열, 정렬은 숫자 값으로."""

    def __init__(self, text, value):
        super().__init__(text)
        self.setData(Qt.ItemDataRole.UserRole, value)

    def __lt__(self, other):
        a, b = self.data(Qt.ItemDataRole.UserRole), other.data(Qt.ItemDataRole.UserRole)
        if a is None or b is None:
            return super().__lt__(other)
        return a < b


def fill_table(table: QTableWidget, frame: pd.DataFrame, signed_cols=(), fmt="{:,.2f}"):
    """DataFrame(인덱스 포함)을 표에 채운다. signed_cols는 +/-에 따라 색을 입힌다."""
    frame = frame.reset_index()
    table.setSortingEnabled(False)
    table.clear()
    table.setRowCount(len(frame))
    table.setColumnCount(len(frame.columns))
    table.setHorizontalHeaderLabels([str(c) for c in frame.columns])
    for r, row in enumerate(frame.itertuples(index=False)):
        for c, val in enumerate(row):
            col = frame.columns[c]
            if isinstance(val, pd.Timestamp):
                item = NumericItem(f"{val:%Y-%m-%d}", val.value)
            elif pd.isna(val):
                item = NumericItem("-", None)
            elif isinstance(val, (int, float)) and not isinstance(val, bool):
                is_int = (c == 0 and float(val).is_integer()) or col == "거래일"
                text = f"{int(val)}" if is_int else fmt.format(val)
                item = NumericItem(text, float(val))
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col in signed_cols and val != 0:
                    item.setForeground(QColor(RISE_COLOR if val > 0 else FALL_COLOR))
            else:
                item = NumericItem(str(val), None)
            table.setItem(r, c, item)
    table.setSortingEnabled(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)


def make_table() -> QTableWidget:
    table = QTableWidget()
    table.setAlternatingRowColors(True)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.verticalHeader().setVisible(False)
    return table


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("S&P 500 Analyzer")
        self.resize(1280, 900)
        self.clean_df = None      # 클렌징만 끝난 전체 데이터
        self.result = None        # (df, yearly, by_month, summary) - 선택 기간 분석 결과
        self.report = ""
        self.period = None        # 라인그래프에 그린 종가 Series (호버용)

        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(18, 18, 18, 12)
        root.setSpacing(12)

        root.addWidget(self._build_banner())
        root.addWidget(self._build_controls())
        root.addLayout(self._build_kpis())
        root.addWidget(self._build_tabs(), stretch=1)

        self.status_label = QLabel("CSV 파일을 불러오세요.", objectName="status")
        root.addWidget(self.status_label)

        if sa.DEFAULT_CSV.exists():
            self.path_edit.setText(str(sa.DEFAULT_CSV))
            self.load_csv()

    # ---------- 화면 구성 ----------
    def _build_banner(self):
        banner = QFrame(objectName="banner")
        lay = QVBoxLayout(banner)
        lay.setContentsMargins(22, 16, 22, 16)
        lay.addWidget(QLabel("📈 S&P 500 데이터 분석", objectName="bannerTitle"))
        self.banner_sub = QLabel("과거 시세 CSV 클렌징 · Pandas 다각도 분석 · 종가 라인그래프", objectName="bannerSub")
        lay.addWidget(self.banner_sub)
        return banner

    def _build_controls(self):
        card = QFrame(objectName="card")
        lay = QHBoxLayout(card)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(8)

        self.path_edit = QLineEdit(placeholderText="S&P 500 과거 데이터 CSV 경로")
        self.path_edit.returnPressed.connect(self.load_csv)
        browse_btn = QPushButton("📂 파일 열기")
        browse_btn.clicked.connect(self.browse_csv)

        self.start_edit = QDateEdit(DEFAULT_START, calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.end_edit = QDateEdit(DEFAULT_END, calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.run_btn = QPushButton("▶ 분석 실행", objectName="primary")
        self.run_btn.clicked.connect(self.run_analysis)
        self.save_btn = QPushButton("💾 결과 저장")
        self.save_btn.clicked.connect(self.save_results)
        self.run_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

        lay.addWidget(self.path_edit, stretch=1)
        lay.addWidget(browse_btn)
        lay.addSpacing(10)
        lay.addWidget(QLabel("기간"))
        lay.addWidget(self.start_edit)
        lay.addWidget(QLabel("~"))
        lay.addWidget(self.end_edit)
        lay.addSpacing(10)
        lay.addWidget(self.run_btn)
        lay.addWidget(self.save_btn)
        return card

    def _build_kpis(self):
        lay = QHBoxLayout()
        lay.setSpacing(10)
        self.kpi_labels = {}
        for key in ("기간", "최종 종가", "누적 수익률", "CAGR", "연환산 변동성", "MDD"):
            card = QFrame(objectName="card")
            v = QVBoxLayout(card)
            v.setContentsMargins(14, 10, 14, 10)
            v.setSpacing(2)
            v.addWidget(QLabel(key, objectName="kpiTitle"))
            value = QLabel("-", objectName="kpiValue")
            if key == "기간":
                value.setStyleSheet("font-size: 11pt;")
            v.addWidget(value)
            self.kpi_labels[key] = value
            lay.addWidget(card, stretch=2 if key == "기간" else 1)
        return lay

    def _build_tabs(self):
        self.tabs = QTabWidget()

        # 종가 라인그래프 (+ 확대/이동 툴바, 마우스 호버 툴팁)
        self.close_fig = Figure(figsize=(12, 5.5), facecolor=THEME["bg"])
        self.close_canvas = FigureCanvasQTAgg(self.close_fig)
        self.close_canvas.mpl_connect("motion_notify_event", self.on_hover)
        page = QWidget()
        v = QVBoxLayout(page)
        v.addWidget(NavigationToolbar2QT(self.close_canvas, page))
        v.addWidget(self.close_canvas)
        self.tabs.addTab(page, "종가 라인그래프")

        # 다각도 분석 대시보드 (세로로 길어서 스크롤)
        self.dash_fig = Figure(figsize=(12, 11), facecolor=THEME["bg"])
        self.dash_canvas = FigureCanvasQTAgg(self.dash_fig)
        self.dash_canvas.setMinimumHeight(1050)
        scroll = QScrollArea(widgetResizable=True)
        scroll.setWidget(self.dash_canvas)
        self.tabs.addTab(scroll, "다각도 분석")

        self.yearly_table = make_table()
        self.tabs.addTab(self.yearly_table, "연도별 성과")
        self.month_table = make_table()
        self.tabs.addTab(self.month_table, "월별 계절성")

        self.report_view = QPlainTextEdit(readOnly=True)
        self.report_view.setFont(QFont("D2Coding, Consolas, Malgun Gothic", 10))
        self.report_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.tabs.addTab(self.report_view, "분석 리포트")

        self.data_table = make_table()
        self.tabs.addTab(self.data_table, "정제 데이터")
        return self.tabs

    # ---------- 불러오기 & 분석 ----------
    def browse_csv(self):
        start_dir = self.path_edit.text() or str(sa.DEFAULT_CSV.parent)
        path, _ = QFileDialog.getOpenFileName(self, "CSV 파일 선택", start_dir, "CSV 파일 (*.csv);;모든 파일 (*)")
        if path:
            self.path_edit.setText(path)
            self.load_csv()

    def load_csv(self):
        path = Path(self.path_edit.text().strip().strip('"'))
        if not path.is_file():
            QMessageBox.warning(self, "파일 없음", f"파일을 찾을 수 없습니다:\n{path}")
            return
        lines = []
        try:
            self.clean_df = sa.load_and_clean(path, log=lines.append)
        except Exception as e:  # 형식이 다른 CSV 등
            self.clean_df = None
            self.run_btn.setEnabled(False)
            QMessageBox.critical(self, "불러오기 실패", str(e))
            return
        self.clean_log = "\n".join(lines)

        # 날짜 선택 범위를 데이터 기간으로 제한
        first, last = self.clean_df.index[0], self.clean_df.index[-1]
        qfirst, qlast = QDate(first.year, first.month, first.day), QDate(last.year, last.month, last.day)
        for edit in (self.start_edit, self.end_edit):
            edit.setDateRange(qfirst, qlast)
        self.start_edit.setDate(max(DEFAULT_START, qfirst))
        self.end_edit.setDate(min(DEFAULT_END, qlast))

        self.banner_sub.setText(f"{path.name}  ·  {len(self.clean_df):,}거래일  ·  "
                                f"{first:%Y-%m-%d} ~ {last:%Y-%m-%d}")
        self.run_btn.setEnabled(True)
        self.run_analysis()

    def run_analysis(self):
        if self.clean_df is None:
            return
        start = self.start_edit.date().toString("yyyy-MM-dd")
        end = self.end_edit.date().toString("yyyy-MM-dd")
        if start > end:
            QMessageBox.warning(self, "기간 오류", "시작일이 종료일보다 늦습니다.")
            return
        subset = self.clean_df.loc[start:end]
        lines = []
        try:
            self.result = sa.analyze(subset, log=lines.append)
        except Exception as e:
            QMessageBox.critical(self, "분석 실패", str(e))
            return
        df, yearly, by_month, summary = self.result
        self.report = f"{self.clean_log}\n\n[분석 기간: {start} ~ {end}]\n" + "\n".join(lines)

        for key, label in self.kpi_labels.items():
            label.setText(summary[key])
            if key in ("누적 수익률", "MDD"):
                negative = summary[key].startswith("-")
                label.setStyleSheet(f"color: {FALL_COLOR if negative else RISE_COLOR};")

        self.period = sa.draw_close_line(self.close_fig, df, start, end, theme="dark")
        self._init_hover()
        self.close_canvas.draw()
        sa.draw_dashboard(self.dash_fig, df, yearly, by_month, theme="dark")
        self.dash_canvas.draw()

        fill_table(self.yearly_table, yearly, signed_cols={"연수익률%"})
        fill_table(self.month_table, by_month, signed_cols={"평균%", "중앙값%"})
        fill_table(self.data_table, df[["Close", "Open", "High", "Low", "ChangePct", "MA50", "MA200", "Drawdown"]]
                   .rename(columns={"Close": "종가", "Open": "시가", "High": "고가", "Low": "저가",
                                    "ChangePct": "변동%", "Drawdown": "낙폭%"}).sort_index(ascending=False),
                   signed_cols={"변동%"})
        self.data_table.sortItems(0, Qt.SortOrder.DescendingOrder)
        self.report_view.setPlainText(self.report)

        self.save_btn.setEnabled(True)
        self.status_label.setText(f"✅ 분석 완료: {start} ~ {end}, {len(df):,}거래일")

    # ---------- 라인그래프 호버 ----------
    def _init_hover(self):
        ax = self.close_fig.axes[0]
        self.hover_line = ax.axvline(self.period.index[0] if len(self.period) else 0,
                                     color=THEME["muted"], linewidth=0.8, linestyle="--", visible=False)
        self.hover_dot = ax.scatter([], [], s=40, color=THEME["blue"], edgecolor=THEME["ink"], zorder=4)
        self.hover_text = ax.annotate("", (0, 0), textcoords="offset points", xytext=(12, 12), fontsize=9,
                                      color=THEME["ink"], visible=False,
                                      bbox=dict(boxstyle="round,pad=0.4", fc="#0f172a", ec=THEME["grid"]))

    def on_hover(self, event):
        if self.period is None or self.period.empty or event.inaxes is None or event.xdata is None:
            if self.period is not None and not self.period.empty and self.hover_text.get_visible():
                self.hover_line.set_visible(False)
                self.hover_text.set_visible(False)
                self.hover_dot.set_offsets([[float("nan"), float("nan")]])
                self.close_canvas.draw_idle()
            return
        x = pd.Timestamp(mdates.num2date(event.xdata)).tz_localize(None)
        i = min(self.period.index.searchsorted(x), len(self.period) - 1)
        date, val = self.period.index[i], self.period.iloc[i]
        xnum = mdates.date2num(date)
        self.hover_line.set_xdata([xnum, xnum])
        self.hover_line.set_visible(True)
        self.hover_dot.set_offsets([[xnum, val]])
        self.hover_text.xy = (xnum, val)
        self.hover_text.set_text(f"{date:%Y-%m-%d}\n종가 {val:,.2f}")
        # 오른쪽 끝에서는 툴팁을 왼쪽으로
        right_half = i > len(self.period) * 0.8
        self.hover_text.set_position((-12, 12) if right_half else (12, 12))
        self.hover_text.set_horizontalalignment("right" if right_half else "left")
        self.hover_text.set_visible(True)
        self.close_canvas.draw_idle()

    # ---------- 저장 ----------
    def save_results(self):
        if self.result is None:
            return
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", str(default_save_dir()))
        if not folder:
            return
        folder = Path(folder)
        df = self.result[0]
        start, end = df.index[0], df.index[-1]
        tag = f"{start:%Y%m}_{end:%Y%m}"
        try:
            # 저장용 그림은 흰 배경(라이트 테마)으로 새로 그린다
            fig = Figure(figsize=(13, 6))
            sa.draw_close_line(fig, df, f"{start:%Y-%m-%d}", f"{end:%Y-%m-%d}", theme="light")
            fig.savefig(folder / f"sp500_close_{tag}.png", dpi=150)
            fig = Figure(figsize=(15, 14))
            sa.draw_dashboard(fig, df, self.result[1], self.result[2], theme="light")
            fig.savefig(folder / f"sp500_dashboard_{tag}.png", dpi=130)
            df.to_csv(folder / f"sp500_cleaned_{tag}.csv", encoding="utf-8-sig")
            (folder / f"sp500_report_{tag}.txt").write_text(self.report, encoding="utf-8")
        except OSError as e:
            QMessageBox.critical(self, "저장 실패", str(e))
            return
        self.status_label.setText(f"💾 저장 완료: {folder} (PNG 2개, CSV, 리포트 TXT)")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    if resource_path("app.ico").exists():
        app.setWindowIcon(QIcon(str(resource_path("app.ico"))))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
