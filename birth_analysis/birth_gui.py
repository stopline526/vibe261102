"""
대한민국 출생아수 분석 GUI (PyQt6)

사용법:
    pip install pandas openpyxl matplotlib PyQt6
    python birth_gui.py

엑셀 불러오기 -> 클랜징 -> 선택 기간 다각도 분석 -> 그래프/표/리포트 확인 -> 결과 저장.
클랜징·분석·그래프는 birth_analysis.py, plot_births.py의 함수를 그대로 사용한다.
"""

import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

import birth_analysis as ba
import plot_births as pb  # 한글 폰트 설정 포함

KOREAN_HEADERS = {
    "births": "출생아수(명)",
    "natural_increase": "자연증가건수(명)",
    "crude_birth_rate": "조출생률(천명당)",
    "natural_increase_rate": "자연증가율(천명당)",
    "tfr": "합계출산율(명)",
    "sex_ratio": "출생성비",
    "births_yoy": "전년대비 증감(명)",
    "births_yoy_pct": "전년대비 증감률(%)",
    "births_ma5": "5년 이동평균",
    "births_idx_1970": "시작연도=100 지수",
    "deaths_est": "사망자수(역산)",
}
COUNT_COLUMNS = {"births", "natural_increase", "births_yoy", "births_ma5", "deaths_est"}  # 정수(명) 표시

STYLESHEET = """
QMainWindow, QWidget#central { background: #f6f7f9; }
QWidget { font-size: 10pt; color: #1f2328; }
QLabel { background: transparent; }
QFrame#card { background: white; border: 1px solid #e5e7eb; border-radius: 10px; }
QLabel#cardTitle { color: #6b7280; font-size: 9pt; }
QLabel#cardValue { font-size: 16pt; font-weight: 600; }
QLabel#cardSub { color: #6b7280; font-size: 8.5pt; }
QPushButton {
    background: white; border: 1px solid #d0d7de; border-radius: 6px; padding: 6px 14px;
}
QPushButton:hover { background: #eef2f7; }
QPushButton#primary { background: #2a6fdb; color: white; border: none; }
QPushButton#primary:hover { background: #1f5bbf; }
QComboBox { background: white; border: 1px solid #d0d7de; border-radius: 6px; padding: 4px 6px; }
QTabWidget::pane { border: 1px solid #e5e7eb; border-radius: 8px; background: white; }
QTabBar::tab { padding: 8px 18px; background: transparent; color: #6b7280; }
QTabBar::tab:selected { color: #2a6fdb; border-bottom: 2px solid #2a6fdb; }
QTableWidget { gridline-color: #eef0f3; border: none; }
QHeaderView::section { background: #f6f7f9; border: none; border-bottom: 1px solid #e5e7eb; padding: 6px; }
QPlainTextEdit { border: none; font-family: Consolas, "Malgun Gothic"; font-size: 9.5pt; }
"""


class StatCard(QFrame):
    def __init__(self, title: str):
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        self.title = QLabel(title, objectName="cardTitle")
        self.value = QLabel("-", objectName="cardValue")
        self.sub = QLabel("", objectName="cardSub")
        for w in (self.title, self.value, self.sub):
            layout.addWidget(w)

    def set(self, value: str, sub: str = "") -> None:
        self.value.setText(value)
        self.sub.setText(sub)


class BirthAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("대한민국 출생아수 분석기")
        self.resize(1200, 820)
        self.df_clean = None  # 클랜징된 전체 데이터
        self.df_result = None  # 선택 기간 분석 결과
        self.report = ""

        central = QWidget(objectName="central")
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # 상단 컨트롤 바
        bar = QHBoxLayout()
        self.btn_open = QPushButton("엑셀 불러오기")
        self.file_label = QLabel("파일을 불러오세요", styleSheet="color:#6b7280;")
        self.start_spin, self.end_spin = QSpinBox(), QSpinBox()
        self.btn_apply = QPushButton("분석 실행", objectName="primary")
        self.btn_save = QPushButton("결과 저장")
        bar.addWidget(self.btn_open)
        bar.addWidget(self.file_label, 1)
        bar.addWidget(QLabel("기간"))
        bar.addWidget(self.start_spin)
        bar.addWidget(QLabel("~"))
        bar.addWidget(self.end_spin)
        bar.addWidget(self.btn_apply)
        bar.addWidget(self.btn_save)
        root.addLayout(bar)

        # 요약 카드
        cards = QHBoxLayout()
        self.card_last = StatCard("최근 출생아수")
        self.card_peak = StatCard("최대 출생아수")
        self.card_low = StatCard("최저 출생아수")
        self.card_tfr = StatCard("최근 합계출산율")
        self.card_cagr = StatCard("연평균 증감률(CAGR)")
        for c in (self.card_last, self.card_peak, self.card_low, self.card_tfr, self.card_cagr):
            cards.addWidget(c)
        root.addLayout(cards)

        # 탭: 그래프 / 데이터 / 리포트
        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        chart_tab = QWidget()
        chart_layout = QVBoxLayout(chart_tab)
        chart_top = QHBoxLayout()
        self.indicator_combo = QComboBox()
        for key, (title, *_rest) in pb.INDICATORS.items():
            self.indicator_combo.addItem(title, key)
        chart_top.addWidget(QLabel("지표"))
        chart_top.addWidget(self.indicator_combo)
        chart_top.addStretch(1)
        self.figure = Figure(figsize=(11, 5.5), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        chart_top.addWidget(NavigationToolbar2QT(self.canvas, self))
        chart_layout.addLayout(chart_top)
        chart_layout.addWidget(self.canvas, 1)
        self.tabs.addTab(chart_tab, "그래프")

        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.tabs.addTab(self.table, "데이터")

        self.report_view = QPlainTextEdit(readOnly=True)
        self.tabs.addTab(self.report_view, "분석 리포트")

        self.btn_open.clicked.connect(self.open_file)
        self.btn_apply.clicked.connect(self.run_analysis)
        self.btn_save.clicked.connect(self.save_results)
        self.indicator_combo.currentIndexChanged.connect(self.draw_chart)
        self.set_enabled(False)

        if ba.SRC.exists():
            self.load(ba.SRC)

    # ---------------------------------------------------------------- 데이터
    def set_enabled(self, enabled: bool) -> None:
        for w in (self.start_spin, self.end_spin, self.btn_apply, self.btn_save, self.indicator_combo):
            w.setEnabled(enabled)

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "출생아수 엑셀 선택", str(Path.home() / "Downloads"),
                                              "Excel (*.xlsx *.xls)")
        if path:
            self.load(Path(path))

    def load(self, path: Path) -> None:
        try:
            with redirect_stdout(io.StringIO()) as buf:
                self.df_clean = ba.load_and_clean(path)
        except Exception as e:  # 형식이 다른 파일 등
            QMessageBox.critical(self, "불러오기 실패", f"{path.name}\n\n{e}")
            return
        self.clean_log = buf.getvalue()
        first, last = int(self.df_clean.index.min()), int(self.df_clean.index.max())
        for spin, value in ((self.start_spin, max(first, 1970)), (self.end_spin, min(last, 2025))):
            spin.blockSignals(True)
            spin.setRange(first, last)
            spin.setValue(value)
            spin.blockSignals(False)
        self.file_label.setText(f"{path.name}  ·  {first}~{last}년, {len(self.df_clean)}개 연도")
        self.set_enabled(True)
        self.run_analysis()

    def run_analysis(self) -> None:
        start, end = self.start_spin.value(), self.end_spin.value()
        if start >= end:
            QMessageBox.warning(self, "기간 오류", "시작 연도는 끝 연도보다 작아야 합니다.")
            return
        df = self.df_clean.loc[start:end]
        with redirect_stdout(io.StringIO()) as buf:
            self.df_result = ba.analyze(df)
        self.report = self.clean_log + buf.getvalue()
        self.report_view.setPlainText(self.report)
        self.update_cards()
        self.fill_table()
        self.draw_chart()

    # ---------------------------------------------------------------- 화면
    def update_cards(self) -> None:
        df = self.df_result
        births = df["births"]
        first, last = df.index[0], df.index[-1]
        yoy = df.loc[last, "births_yoy_pct"]
        cagr = (births.iloc[-1] / births.iloc[0]) ** (1 / (last - first)) - 1
        self.card_last.set(f"{births.iloc[-1]:,}명", f"{last}년 · 전년 대비 {yoy:+.1f}%")
        self.card_peak.set(f"{births.max():,}명", f"{births.idxmax()}년")
        self.card_low.set(f"{births.min():,}명", f"{births.idxmin()}년")
        self.card_tfr.set(f"{df.loc[last, 'tfr']:.2f}명", f"{last}년 · 최저 {df['tfr'].min():.2f} ({df['tfr'].idxmin()}년)")
        self.card_cagr.set(f"{cagr * 100:+.2f}%", f"{first}~{last}년")

    def fill_table(self) -> None:
        df = self.df_result.drop(columns=["decade"])
        self.table.clear()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns) + 1)
        self.table.setHorizontalHeaderLabels(["연도"] + [KOREAN_HEADERS.get(c, c) for c in df.columns])
        align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for r, (year, row) in enumerate(df.iterrows()):
            self.table.setItem(r, 0, QTableWidgetItem(str(year)))
            for c, value in enumerate(row, start=1):
                column = df.columns[c - 1]
                if value != value:  # NaN
                    text = ""
                elif column in COUNT_COLUMNS:
                    text = f"{value:,.0f}"
                elif column == "sex_ratio":
                    text = f"{value:.1f}"
                else:
                    text = f"{value:,.2f}"
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if column in ("births_yoy", "births_yoy_pct", "natural_increase") and value < 0:
                    item.setForeground(Qt.GlobalColor.red)
                self.table.setItem(r, c, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)

    def draw_chart(self) -> None:
        if self.df_result is None:
            return
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        pb.draw_chart(ax, self.df_result, self.indicator_combo.currentData())
        self.figure.text(0.01, 0.01, "자료: 통계청 「인구동향조사」 (KOSIS)", fontsize=8, color=pb.MUTED)
        self.figure.tight_layout()
        self.canvas.draw_idle()

    # ---------------------------------------------------------------- 저장
    def save_results(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "저장할 폴더 선택", str(ba.OUT_DIR))
        if not folder:
            return
        out = Path(folder)
        start, end = self.df_result.index[0], self.df_result.index[-1]
        tag = f"{start}_{end}"
        self.df_result.to_csv(out / f"births_analysis_{tag}.csv", encoding="utf-8-sig")
        (out / f"analysis_report_{tag}.txt").write_text(self.report, encoding="utf-8")
        chart = out / f"chart_{self.indicator_combo.currentData()}_{tag}.png"
        self.figure.savefig(chart, dpi=150, bbox_inches="tight")
        QMessageBox.information(self, "저장 완료", f"{out}\n\n- 분석 CSV\n- 분석 리포트 TXT\n- 그래프 PNG")


def main() -> None:
    app = QApplication(sys.argv)
    # Windows 다크 모드에서도 밝은 테마 고정 (그래프 툴바 아이콘 색이 배경 밝기를 따라감)
    app.setStyle("Fusion")
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setFont(QFont("Malgun Gothic", 10))
    app.setStyleSheet(STYLESHEET)
    window = BirthAnalyzer()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
