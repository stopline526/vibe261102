"""대한민국 출생아수 1970~2025 라인 그래프."""
import sys

import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib import font_manager

from birth_analysis import OUT_DIR, SRC, load_and_clean

# 한글 폰트 (Windows: 맑은 고딕, macOS: AppleGothic)
for name in ["Malgun Gothic", "AppleGothic", "NanumGothic"]:
    if any(f.name == name for f in font_manager.fontManager.ttflist):
        plt.rcParams["font.family"] = name
        break
plt.rcParams["axes.unicode_minus"] = False

LINE = "#2a6fdb"
INK, MUTED, GRID = "#1f2328", "#6b7280", "#e5e7eb"

# GUI에서 고를 수 있는 지표: 컬럼 -> (제목, y축 라벨, 눈금 포맷, 주석 값 포맷)
INDICATORS = {
    "births": ("연간 출생아수", "출생아수 (명)", lambda v, _: f"{v / 10000:,.0f}만", "{:,.0f}명"),
    "tfr": ("합계출산율", "합계출산율 (명)", lambda v, _: f"{v:.1f}", "{:.2f}명"),
    "natural_increase": ("자연증가건수 (출생 - 사망)", "자연증가 (명)", lambda v, _: f"{v / 10000:,.0f}만", "{:,.0f}명"),
    "crude_birth_rate": ("조출생률", "인구 천 명당 (명)", lambda v, _: f"{v:.0f}", "{:.1f}명"),
    "sex_ratio": ("출생성비", "여아 100명당 남아 (명)", lambda v, _: f"{v:.0f}", "{:.1f}"),
}


def draw_chart(ax, df, column="births"):
    """df[column]을 라인 그래프로 그린다. 최대·최저·최근값만 주석으로 표시."""
    title, ylabel, tick_fmt, value_fmt = INDICATORS[column]
    series = df[column]
    first, last = series.index[0], series.index[-1]

    ax.plot(series.index, series.values, color=LINE, linewidth=2, marker="o", markersize=3.5)
    baseline = min(0, series.min())
    ax.fill_between(series.index, series.values, 0, color=LINE, alpha=0.06)
    if series.min() < 0:
        ax.axhline(0, color=MUTED, linewidth=0.8)

    # 선택적 주석: 최대(위), 최저(아래), 최근값(위) - 겹치지 않도록 위치 분리
    annotations = [
        (series.idxmax(), "최대", (0, 12), "bottom"),
        (series.idxmin(), "최저", (0, -14), "top"),
        (last, "", (0, 12), "bottom"),
    ]
    seen = set()
    for year, label, offset, va in annotations:
        if year in seen:
            continue
        seen.add(year)
        value = series[year]
        ax.scatter(year, value, s=50, color=LINE, edgecolor="white", linewidth=1.5, zorder=3)
        text = f"{label} {year}년\n{value_fmt.format(value)}".strip()
        ax.annotate(text, (year, value), xytext=offset, textcoords="offset points",
                    ha="center", va=va, fontsize=9, color=INK)

    span = series.max() - baseline
    ax.set_title(f"대한민국 {title} ({first}~{last})", fontsize=15, color=INK, loc="left", pad=14)
    ax.set_xlabel("연도", color=MUTED)
    ax.set_ylabel(ylabel, color=MUTED)
    ax.set_xlim(first - 1, last + 1.5)
    ax.set_ylim(baseline - (span * 0.15 if baseline < 0 else 0), series.max() + span * 0.15)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=12, integer=True))
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(tick_fmt))
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=MUTED)
    for side in ["top", "right", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    df = load_and_clean(SRC).loc[1970:2025]

    fig, ax = plt.subplots(figsize=(12, 6), dpi=150)
    draw_chart(ax, df, "births")
    fig.text(0.01, 0.01, "자료: 통계청 「인구동향조사」 (KOSIS)", fontsize=8, color=MUTED)

    fig.tight_layout()
    out = OUT_DIR / "births_1970_2025.png"
    OUT_DIR.mkdir(exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    print(f"저장: {out}")
    plt.show()


if __name__ == "__main__":
    main()
