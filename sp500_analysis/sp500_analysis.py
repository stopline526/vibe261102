"""S&P 500 과거 데이터 클렌징 + Pandas 다각도 분석 + 종가 라인그래프.

GUI(sp500_gui.py)와 명령줄 양쪽에서 쓰는 분석/그래프 모듈.
분석 결과 텍스트는 log 함수로 내보내고(기본 print), 그래프는 전달받은 Figure에 그린다.

명령줄 사용법:
    python sp500_analysis.py ["S&P 500 과거 데이터.csv 경로"]
결과물(정제 CSV, 그래프 PNG)은 이 스크립트 옆 output/ 폴더에 저장된다.
"""
import sys
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

DEFAULT_CSV = Path.home() / "Downloads" / "S&P 500 과거 데이터.csv"
OUT_DIR = Path(__file__).resolve().parent / "output"

# 그래프 스타일 (한글 폰트 + 차분한 축/격자). 다크 테마는 어두운 배경용으로 따로 고른 색.
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
THEMES = {
    "light": dict(bg="#fcfcfb", ink="#0b0b0b", muted="#52514e", grid="#e4e3df",
                  blue="#2a78d6", orange="#eb6834", aqua="#1baf7a"),
    "dark": dict(bg="#1e293b", ink="#f0efec", muted="#c3c2b7", grid="#334155",
                 blue="#3987e5", orange="#d95926", aqua="#199e70"),
}

pd.set_option("display.width", 120)
pd.set_option("display.float_format", "{:,.2f}".format)


def section(log, title):
    log(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ----------------------------------------------------------------------------
# 1. 데이터 로드 & 클렌징
# ----------------------------------------------------------------------------
def load_and_clean(path, log=print):
    raw = pd.read_csv(path, encoding="utf-8-sig", dtype=str)
    section(log, "1. 원본 데이터 개요 & 클렌징")
    log(f"행 x 열: {raw.shape}")
    log(raw.head().to_string())
    log("\n[컬럼별 결측치]")
    log(raw.isna().sum().to_string())

    df = raw.rename(columns={
        "날짜": "Date", "종가": "Close", "시가": "Open", "고가": "High",
        "저가": "Low", "거래량": "Volume", "변동 %": "ChangePct",
    })
    missing = {"Date", "Close", "Open", "High", "Low", "ChangePct"} - set(df.columns)
    if missing:
        raise ValueError(f"필요한 컬럼이 없습니다: {sorted(missing)}\n(날짜, 종가, 시가, 고가, 저가, 변동 % 형식의 CSV가 필요합니다)")

    # 날짜: "2019- 11- 14" 처럼 공백이 섞인 문자열 -> datetime
    df["Date"] = pd.to_datetime(df["Date"].str.replace(" ", ""), format="%Y-%m-%d", errors="coerce")

    # 가격: 천 단위 콤마 제거 -> float
    for col in ["Close", "Open", "High", "Low"]:
        df[col] = pd.to_numeric(df[col].str.replace(",", ""), errors="coerce")

    # 변동률: "-0.20%" -> -0.20
    df["ChangePct"] = pd.to_numeric(df["ChangePct"].str.replace("%", ""), errors="coerce")

    # 거래량: 전부 비어 있으면 분석 가치가 없으므로 제거
    if "Volume" in df and df["Volume"].isna().all():
        df = df.drop(columns="Volume")
        log("\n- 거래량 컬럼은 100% 결측 -> 제거")

    before = len(df)
    df = df.dropna(subset=["Date", "Close"])
    df = df.drop_duplicates(subset="Date")
    df = df[(df[["Close", "Open", "High", "Low"]] > 0).all(axis=1)]

    # 가격 논리 검증: 고가 >= max(시가, 종가, 저가), 저가 <= min(...)
    # 행을 지우면 다음 날 수익률이 이틀치로 왜곡되므로, 고가/저가를 보정한다.
    ohlc = df[["Open", "High", "Low", "Close"]]
    bad = (df["High"] < ohlc.max(axis=1)) | (df["Low"] > ohlc.min(axis=1))
    if bad.any():
        log(f"\n- 가격 논리 오류 {bad.sum()}행 -> 고가/저가 보정:\n{df[bad].to_string()}")
        df.loc[bad, "High"] = ohlc[bad].max(axis=1)
        df.loc[bad, "Low"] = ohlc[bad].min(axis=1)

    # 시간 오름차순 정렬 후 Date 인덱스화
    df = df.sort_values("Date").set_index("Date")
    log(f"- 결측/중복/오류 제거: {before} -> {len(df)} 행")
    log(f"- 기간: {df.index.min():%Y-%m-%d} ~ {df.index.max():%Y-%m-%d}")
    log("\n[정제 후 dtypes]")
    log(df.dtypes.to_string())
    return df


# ----------------------------------------------------------------------------
# 2. 다각도 분석
# ----------------------------------------------------------------------------
def analyze(df, log=print):
    """지표를 덧붙인 df, 연도별 표, 월별 표, 핵심 지표 dict를 돌려준다."""
    if len(df) < 2:
        raise ValueError("분석하려면 최소 2거래일 이상의 데이터가 필요합니다.")
    df = df.copy()
    df["Return"] = df["Close"].pct_change() * 100          # 일간 수익률(%)
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    df["Vol20"] = df["Return"].rolling(20).std() * np.sqrt(252)  # 연환산 변동성(%)
    df["Peak"] = df["Close"].cummax()
    df["Drawdown"] = (df["Close"] / df["Peak"] - 1) * 100
    df["Range"] = (df["High"] - df["Low"]) / df["Open"] * 100  # 일중 변동폭(%)

    section(log, "2. 기술통계")
    log(df[["Close", "Open", "High", "Low", "Return", "Range"]].describe().to_string())

    # 원본 '변동 %'와 계산 수익률이 일치하는지 교차검증
    diff = (df["Return"] - df["ChangePct"]).abs()
    log(f"\n- 원본 변동% vs 계산 수익률 최대 오차: {diff.max():.3f}%p")

    section(log, "3. 연도별 성과")
    yearly = df.groupby(df.index.year).agg(
        시작가=("Close", "first"), 종가=("Close", "last"),
        최고=("High", "max"), 최저=("Low", "min"),
        일변동성=("Return", "std"), 거래일=("Close", "size"),
    )
    yearly.index.name = "연도"
    yearly["연수익률%"] = (yearly["종가"] / yearly["종가"].shift(1) - 1) * 100
    first_year = yearly.index[0]
    yearly.loc[first_year, "연수익률%"] = (yearly.loc[first_year, "종가"] / df["Open"].iloc[0] - 1) * 100
    yearly["연환산변동성%"] = yearly["일변동성"] * np.sqrt(252)
    yearly = yearly.drop(columns="일변동성")
    log(yearly.to_string())
    log(f"\n- 상승한 해: {(yearly['연수익률%'] > 0).sum()} / {len(yearly)}")
    log(f"- 최고의 해: {yearly['연수익률%'].idxmax()} ({yearly['연수익률%'].max():+.1f}%)")
    log(f"- 최악의 해: {yearly['연수익률%'].idxmin()} ({yearly['연수익률%'].min():+.1f}%)")
    if df.index.max().month < 12:
        log(f"  ※ {df.index.max().year}년은 {df.index.max():%m-%d}까지의 부분 데이터")

    section(log, "4. 전체 기간 수익률")
    years = max((df.index[-1] - df.index[0]).days / 365.25, 1 / 365.25)
    total = df["Close"].iloc[-1] / df["Close"].iloc[0] - 1
    cagr = (1 + total) ** (1 / years) - 1
    vol = df["Return"].std() * np.sqrt(252)
    log(f"- 누적 수익률: {total * 100:+.1f}%  ({df['Close'].iloc[0]:,.1f} -> {df['Close'].iloc[-1]:,.1f})")
    log(f"- 연평균 성장률(CAGR): {cagr * 100:.2f}%")
    log(f"- 연환산 변동성: {vol:.2f}%")
    log(f"- 상승일 비율: {(df['Return'] > 0).mean() * 100:.1f}%")

    section(log, "5. 최대 낙폭(MDD) 및 회복")
    trough = df["Drawdown"].idxmin()
    peak_date = df.loc[:trough, "Close"].idxmax()
    recovered = df.loc[trough:][df.loc[trough:, "Close"] >= df.loc[peak_date, "Close"]]
    log(f"- MDD: {df['Drawdown'].min():.1f}%")
    log(f"- 고점 {peak_date:%Y-%m-%d} ({df.loc[peak_date, 'Close']:,.1f}) -> 저점 {trough:%Y-%m-%d} ({df.loc[trough, 'Close']:,.1f})")
    if not recovered.empty:
        rec = recovered.index[0]
        log(f"- 전고점 회복: {rec:%Y-%m-%d} (고점 이후 {(rec - peak_date).days / 365.25:.1f}년)")

    # 주요 하락 구간: 고점 -> 전고점 회복까지를 한 구간으로 묶고, 그중 낙폭 -20% 이상만 약세장
    underwater = df["Drawdown"] < 0
    episodes = (~underwater).cumsum()[underwater]
    log("\n[-20% 이상 약세장 구간 (고점 -> 저점 -> 회복)]")
    for _, grp in df[underwater].groupby(episodes):
        if grp["Drawdown"].min() > -20:
            continue
        low = grp["Drawdown"].idxmin()
        pos = df.index.get_loc(grp.index[-1]) + 1  # 수면 위로 올라온 첫 거래일
        end = df.index[pos] if pos < len(df) else None
        log(f"  하락 시작 {grp.index[0]:%Y-%m-%d}  저점 {low:%Y-%m-%d} ({grp['Drawdown'].min():.1f}%)"
            f"  회복 {f'{end:%Y-%m-%d}' if end is not None else '미회복'}")

    section(log, "6. 최대 상승/하락일 Top 5")
    log("[상승]")
    log(df["Return"].nlargest(5).to_frame("수익률%").to_string())
    log("[하락]")
    log(df["Return"].nsmallest(5).to_frame("수익률%").to_string())

    section(log, "7. 월별/요일별 계절성")
    monthly_ret = df["Close"].resample("ME").last().pct_change() * 100
    by_month = monthly_ret.groupby(monthly_ret.index.month).agg(["mean", "median", lambda s: (s > 0).mean() * 100])
    by_month.columns = ["평균%", "중앙값%", "상승확률%"]
    by_month.index.name = "월"
    log(by_month.to_string())
    weekday_names = ["월", "화", "수", "목", "금", "토", "일"]
    by_wd = df.groupby(df.index.dayofweek)["Return"].agg(["mean", "std", "count"])
    by_wd.index = [weekday_names[i] for i in by_wd.index]
    by_wd.columns = ["평균%", "표준편차%", "거래일"]
    log(by_wd.to_string())

    section(log, "8. 수익률 분포")
    r = df["Return"].dropna()
    log(f"- 왜도(skew): {r.skew():.3f}   (음수 = 큰 하락이 더 자주)")
    log(f"- 첨도(kurt): {r.kurt():.3f}   (0보다 크면 정규분포보다 꼬리가 두꺼움)")
    log(f"- |수익률| > 3% 인 날: {(r.abs() > 3).sum()}일 ({(r.abs() > 3).mean() * 100:.2f}%)")
    log(f"- VaR 95% (일간): {r.quantile(0.05):.2f}%")

    section(log, "9. 이동평균 신호 (골든/데드 크로스)")
    above = (df["MA50"] > df["MA200"]).where(df["MA200"].notna())
    cross = above.astype(float).diff()
    log(f"- 골든크로스 {int((cross == 1).sum())}회, 데드크로스 {int((cross == -1).sum())}회")
    for d, v in cross[cross != 0].dropna().items():
        log(f"  {d:%Y-%m-%d}  {'골든' if v > 0 else '데드'}")
    log(f"- MA200 위에 있던 거래일 비율: {(df['Close'] > df['MA200']).mean() * 100:.1f}%")

    summary = {
        "기간": f"{df.index[0]:%Y-%m-%d} ~ {df.index[-1]:%Y-%m-%d}",
        "누적 수익률": f"{total * 100:+.1f}%",
        "CAGR": f"{cagr * 100:.2f}%",
        "연환산 변동성": f"{vol:.1f}%",
        "MDD": f"{df['Drawdown'].min():.1f}%",
        "최종 종가": f"{df['Close'].iloc[-1]:,.1f}",
    }
    return df, yearly, by_month, summary


# ----------------------------------------------------------------------------
# 3. 시각화 (전달받은 Figure에 그림 -> GUI 캔버스/PNG 저장 공용)
# ----------------------------------------------------------------------------
def style_axes(ax, t):
    ax.set_facecolor(t["bg"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(t["muted"])
    ax.tick_params(colors=t["muted"])
    ax.grid(axis="y", color=t["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.title.set_color(t["ink"])
    ax.xaxis.label.set_color(t["muted"])
    ax.yaxis.label.set_color(t["muted"])


def draw_close_line(fig, df, start="2000-01-01", end="2019-12-31", theme="light"):
    """종가 기준 start ~ end 라인그래프. 그린 Series를 돌려준다(GUI 호버용)."""
    t = THEMES[theme]
    fig.clear()
    fig.set_facecolor(t["bg"])
    period = df.loc[start:end, "Close"]
    ax = fig.add_subplot()
    style_axes(ax, t)
    if period.empty:
        ax.text(0.5, 0.5, "선택한 기간에 데이터가 없습니다", ha="center", va="center",
                transform=ax.transAxes, color=t["muted"])
        return period

    ax.plot(period.index, period.values, color=t["blue"], linewidth=1.6)
    ax.set_title(f"S&P 500 종가 ({period.index[0]:%Y.%m} ~ {period.index[-1]:%Y.%m})",
                 fontsize=15, loc="left", pad=12, color=t["ink"])
    ax.set_ylabel("종가 (pt)")
    span_years = (period.index[-1] - period.index[0]).days / 365.25
    if span_years > 4:
        ax.xaxis.set_major_locator(mdates.YearLocator(max(1, round(span_years / 10))))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    else:
        locator = mdates.AutoDateLocator()
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
    ax.set_xlim(period.index[0], period.index[-1])

    # 주요 지점만 선택적으로 라벨링 (최고가 = 최근이면 하나로 합침)
    hi, lo, last = period.idxmax(), period.idxmin(), period.index[-1]
    points = [("최저", lo, (12, -4), "left")]
    if hi == last:
        points.append(("최고·최근", last, (-8, 6), "right"))
    else:
        points += [("최고", hi, (0, 10), "center"), ("최근", last, (-8, 6), "right")]
    for label, date, offset, ha in points:
        val = period[date]
        ax.scatter(date, val, s=36, color=t["blue"], edgecolor=t["bg"], linewidth=1.5, zorder=3)
        ax.annotate(f"{label} {val:,.0f} ({date:%Y-%m-%d})", (date, val),
                    textcoords="offset points", xytext=offset, ha=ha, fontsize=9, color=t["ink"])
    fig.tight_layout()
    return period


def draw_dashboard(fig, df, yearly, by_month, theme="light"):
    t = THEMES[theme]
    fig.clear()
    fig.set_facecolor(t["bg"])
    axes = fig.subplots(3, 2)

    # (1) 종가 + 이동평균
    ax = axes[0, 0]
    ax.plot(df.index, df["Close"], color=t["blue"], linewidth=1.2, label="종가")
    ax.plot(df.index, df["MA50"], color=t["orange"], linewidth=1.2, label="MA50")
    ax.plot(df.index, df["MA200"], color=t["aqua"], linewidth=1.2, label="MA200")
    ax.set_title("종가와 50/200일 이동평균", loc="left", color=t["ink"])
    ax.legend(frameon=False, labelcolor=t["ink"])

    # (2) 연도별 수익률
    ax = axes[0, 1]
    ret = yearly["연수익률%"]
    ax.bar(ret.index, ret, color=np.where(ret >= 0, t["blue"], t["orange"]), width=0.8)
    ax.axhline(0, color=t["muted"], linewidth=0.8)
    ax.set_title("연도별 수익률 (%)", loc="left", color=t["ink"])
    ax.set_xticks(ret.index[::2] if len(ret) > 10 else ret.index)

    # (3) 낙폭
    ax = axes[1, 0]
    ax.fill_between(df.index, df["Drawdown"], 0, color=t["orange"], alpha=0.35, linewidth=0)
    ax.plot(df.index, df["Drawdown"], color=t["orange"], linewidth=1)
    ax.set_title("고점 대비 낙폭 (Drawdown, %)", loc="left", color=t["ink"])

    # (4) 20일 연환산 변동성
    ax = axes[1, 1]
    ax.plot(df.index, df["Vol20"], color=t["blue"], linewidth=1)
    ax.set_title("20일 이동 변동성 (연환산, %)", loc="left", color=t["ink"])

    # (5) 일간 수익률 분포
    ax = axes[2, 0]
    r = df["Return"].dropna()
    ax.hist(r, bins=120, color=t["blue"], alpha=0.85)
    ax.axvline(r.mean(), color=t["ink"], linewidth=1, linestyle="--")
    ax.set_title(f"일간 수익률 분포 (왜도 {r.skew():.2f}, 첨도 {r.kurt():.2f})", loc="left", color=t["ink"])
    ax.set_xlabel("일간 수익률 (%)")

    # (6) 월별 평균 수익률
    ax = axes[2, 1]
    m = by_month["평균%"]
    ax.bar(m.index, m, color=np.where(m >= 0, t["blue"], t["orange"]), width=0.7)
    ax.axhline(0, color=t["muted"], linewidth=0.8)
    ax.set_xticks(range(1, 13), [f"{i}월" for i in range(1, 13)])
    ax.set_title("월별 평균 수익률 (%)", loc="left", color=t["ink"])

    for ax in axes.flat:
        style_axes(ax, t)
    fig.suptitle(f"S&P 500 다각도 분석 ({df.index[0]:%Y} ~ {df.index[-1]:%Y})",
                 fontsize=16, x=0.01, ha="left", color=t["ink"])
    fig.tight_layout()


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    OUT_DIR.mkdir(exist_ok=True)

    df = load_and_clean(csv_path)
    df.to_csv(OUT_DIR / "sp500_cleaned.csv", encoding="utf-8-sig")

    df, yearly, by_month, _ = analyze(df)

    section(print, "10. 그래프 저장")
    fig = plt.figure(figsize=(13, 6))
    draw_close_line(fig, df)
    fig.savefig(OUT_DIR / "sp500_close_2000_2019.png", dpi=150)
    print(f"- 저장: {OUT_DIR / 'sp500_close_2000_2019.png'}")

    fig2 = plt.figure(figsize=(15, 14))
    draw_dashboard(fig2, df, yearly, by_month)
    fig2.savefig(OUT_DIR / "sp500_dashboard.png", dpi=130)
    print(f"- 저장: {OUT_DIR / 'sp500_dashboard.png'}")
    plt.show()


if __name__ == "__main__":
    main()
