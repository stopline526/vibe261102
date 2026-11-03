"""대한민국 출생아수·합계출산율·자연증가 데이터 클랜징 및 다각도 분석 (KOSIS INH_1B8000F_01)."""
import re
import sys
from pathlib import Path

import pandas as pd

BASE = Path(__file__).parent
SRC = BASE / "data" / "births.xlsx"
OUT_DIR = BASE / "output"

# 원본 항목명 -> 분석용 컬럼명
COLUMN_MAP = {
    "출생아수": "births",
    "자연증가건수": "natural_increase",
    "조출생률": "crude_birth_rate",
    "자연증가율": "natural_increase_rate",
    "합계출산율": "tfr",
    "출생성비": "sex_ratio",
}
REPLACEMENT_TFR = 2.1  # 인구대체수준


# ---------------------------------------------------------------- 1. 클랜징
def load_and_clean(path: Path) -> pd.DataFrame:
    raw = pd.read_excel(path, sheet_name=0, header=None)

    # 첫 행 = 연도 헤더, 첫 열 = 항목명 (wide 형식) -> 전치해서 연도별 long 형식으로
    raw = raw.set_index(0)
    header_label = raw.index[0]
    years = raw.loc[header_label]
    df = raw.drop(index=header_label).T
    df.index = years

    # 항목명 정리: "출생아수(명)" -> "출생아수" -> "births"
    df.columns = [re.sub(r"\(.*?\)", "", str(c)).strip() for c in df.columns]
    unknown = set(df.columns) - COLUMN_MAP.keys()
    if unknown:
        raise ValueError(f"예상하지 못한 항목: {unknown}")
    df = df.rename(columns=COLUMN_MAP)

    # 연도: 1970.0 같은 float/문자열 -> int
    df.index = pd.to_numeric(pd.Series(df.index).astype(str).str.extract(r"(\d{4})")[0]).astype(int)
    df.index.name = "year"

    # 값: '-', '…', 쉼표, 공백 등을 처리하고 숫자형으로 변환
    df = df.apply(
        lambda s: pd.to_numeric(
            s.astype(str).str.replace(",", "").str.strip().replace({"-": None, "…": None, "nan": None}),
            errors="coerce",
        )
    )

    # 중복 연도 제거 & 정렬
    df = df[~df.index.duplicated(keep="last")].sort_index()

    # 누락 연도 확인 후 재색인(빈 연도는 선형 보간)
    full = range(df.index.min(), df.index.max() + 1)
    missing_years = sorted(set(full) - set(df.index))
    df = df.reindex(full)
    df.index.name = "year"
    n_missing = int(df.isna().sum().sum())
    if n_missing:
        df = df.interpolate(method="linear", limit_direction="both")

    # 유효 범위 검증
    checks = {
        "births": (df["births"] > 0).all(),
        "tfr": df["tfr"].between(0, 10).all(),
        "sex_ratio": df["sex_ratio"].between(90, 130).all(),
        "crude_birth_rate": df["crude_birth_rate"].between(0, 60).all(),
    }
    failed = [k for k, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"범위 검증 실패: {failed}")

    df["births"] = df["births"].round().astype("int64")
    df["natural_increase"] = df["natural_increase"].round().astype("int64")

    print("[클랜징 결과]")
    print(f"  기간: {df.index.min()}~{df.index.max()} ({len(df)}개 연도)")
    print(f"  누락 연도: {missing_years or '없음'} / 결측치 보간: {n_missing}개")
    print(f"  범위 검증: 통과 ({', '.join(checks)})")
    return df


# ---------------------------------------------------------------- 2. 분석
def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def analyze(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["births_yoy"] = df["births"].diff()
    df["births_yoy_pct"] = df["births"].pct_change() * 100
    df["births_ma5"] = df["births"].rolling(5, center=True).mean()
    df["births_idx_1970"] = df["births"] / df["births"].iloc[0] * 100
    df["decade"] = df.index // 10 * 10

    section("1. 기술통계")
    print(df[list(COLUMN_MAP.values())].describe().T.round(2).to_string())

    section("2. 출생아수 핵심 지표")
    first, last = df.index[0], df.index[-1]
    peak_year, low_year = df["births"].idxmax(), df["births"].idxmin()
    n_years = last - first
    cagr = (df.loc[last, "births"] / df.loc[first, "births"]) ** (1 / n_years) - 1
    print(f"  {first}년 출생아수 : {df.loc[first, 'births']:>10,}명")
    print(f"  {last}년 출생아수 : {df.loc[last, 'births']:>10,}명 ({first}년 대비 {df.loc[last, 'births_idx_1970']:.1f}%)")
    print(f"  최대            : {df.loc[peak_year, 'births']:>10,}명 ({peak_year}년)")
    print(f"  최소            : {df.loc[low_year, 'births']:>10,}명 ({low_year}년)")
    print(f"  연평균 증감률(CAGR, {first}~{last}): {cagr * 100:.2f}%")

    section("3. 연대별 평균")
    decade = df.groupby("decade").agg(
        births_mean=("births", "mean"),
        births_total=("births", "sum"),
        tfr_mean=("tfr", "mean"),
        sex_ratio_mean=("sex_ratio", "mean"),
        natural_increase_mean=("natural_increase", "mean"),
    )
    decade["births_change_pct"] = decade["births_mean"].pct_change() * 100
    print(decade.round(2).to_string(float_format=lambda v: f"{v:,.2f}"))

    section("4. 전년 대비 증감 상위/하위 5개 연도")
    cols = ["births", "births_yoy", "births_yoy_pct", "tfr"]
    print("  [감소폭 큰 해]")
    print(df.nsmallest(5, "births_yoy")[cols].round(2).to_string())
    print("  [증가폭 큰 해]")
    print(df.nlargest(5, "births_yoy")[cols].round(2).to_string())
    up_years = df.index[df["births_yoy"] > 0].tolist()
    print(f"  출생아수 증가 연도({len(up_years)}회): {up_years}")

    section("5. 합계출산율 구간 진입 시점")
    for label, threshold in [
        (f"인구대체수준({REPLACEMENT_TFR}) 미만", REPLACEMENT_TFR),
        ("초저출산(1.3) 미만", 1.3),
        ("1.0 미만", 1.0),
    ]:
        below = df.index[df["tfr"] < threshold]
        print(f"  {label:<22}: {below[0] if len(below) else '해당 없음'}년부터")
    print(f"  최저 합계출산율: {df['tfr'].min():.2f}명 ({df['tfr'].idxmin()}년)")
    print(f"  최근 5년: {df['tfr'].tail(5).round(2).to_dict()}")

    section("6. 자연증가 (출생 - 사망)")
    neg = df.index[df["natural_increase"] < 0]
    print(f"  자연감소 시작: {neg[0] if len(neg) else '없음'}년")
    deaths = df["births"] - df["natural_increase"]  # 사망자수 역산
    df["deaths_est"] = deaths
    print(f"  사망자수(역산) {first}년 {deaths.iloc[0]:,} -> {last}년 {deaths.iloc[-1]:,}")
    print(df.loc[df.index >= 2015, ["births", "deaths_est", "natural_increase", "natural_increase_rate"]].to_string())

    section("7. 출생성비 (여아 100명당 남아)")
    sr = df["sex_ratio"]
    print(f"  최고: {sr.max():.1f} ({sr.idxmax()}년), 최저: {sr.min():.1f} ({sr.idxmin()}년)")
    abnormal = df.index[sr > 107]  # 자연 성비 정상 범위 103~107
    print(f"  정상범위(103~107) 초과 연도: {abnormal.tolist()}")
    normal_since = next((y for y in df.index if (sr.loc[y:] <= 107).all()), None)
    print(f"  {normal_since}년 이후 정상범위 유지")

    section("8. 지표 간 상관관계 (Pearson)")
    print(df[list(COLUMN_MAP.values())].corr().round(3).to_string())

    section("9. 최근 반등 여부")
    recent = df.loc[df.index >= 2015, ["births", "births_yoy_pct", "tfr"]]
    print(recent.round(2).to_string())
    return df


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    OUT_DIR.mkdir(exist_ok=True)
    df = load_and_clean(SRC)
    df.to_csv(OUT_DIR / "births_clean.csv", encoding="utf-8-sig")
    result = analyze(df)
    result.to_csv(OUT_DIR / "births_analysis.csv", encoding="utf-8-sig")
    print(f"\n저장: {OUT_DIR / 'births_clean.csv'}, {OUT_DIR / 'births_analysis.csv'}")


if __name__ == "__main__":
    main()
