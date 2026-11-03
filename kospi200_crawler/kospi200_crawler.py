"""
네이버페이 증권(stock.naver.com)에서 코스피200 지수와 편입종목 시세를 크롤링하는 스크립트

사용법:
    pip install requests
    python kospi200_crawler.py                    # 지수 요약 + 편입종목 200개(20개씩 10페이지) → kospi200.csv
    python kospi200_crawler.py --limit 0          # API가 주는 편입종목 전부
    python kospi200_crawler.py --days 20          # 최근 20거래일 지수 일별 시세도 함께 저장
    python kospi200_crawler.py --out result.xlsx  # 엑셀 파일로 저장 (openpyxl 필요)

참고:
    https://stock.naver.com/market/stock/kr 은 Next.js로 만든 페이지라서 서버가 보내는 HTML에는
    지수·종목 숫자가 들어 있지 않고, 브라우저가 JavaScript로 아래 JSON API를 호출해 화면을 채웁니다.
    그래서 HTML을 BeautifulSoup으로 파싱해도 데이터를 얻을 수 없으므로, 같은 API를 직접 호출합니다.
    (예전 finance.naver.com/sise/entryJongmok.naver 페이지는 "더 이상 제공되지 않습니다"로 바뀌었습니다.)
"""

import argparse
import csv
import time

import requests

API_BASE = "https://m.stock.naver.com/api/index/KPI200"
PAGE_SIZE = 20  # 사이트 화면과 같은 페이지 크기 (60을 넘으면 빈 응답이 옵니다)
MAX_PAGES = 20  # 무한 루프 방지용 상한

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://stock.naver.com/market/stock/kr",
}

STOCK_COLUMNS = {
    "itemCode": "종목코드",
    "stockName": "종목명",
    "closePrice": "현재가",
    "compareToPreviousClosePrice": "전일비",
    "fluctuationsRatio": "등락률(%)",
    "accumulatedTradingVolume": "거래량",
    "accumulatedTradingValue": "거래대금(백만)",
    "marketValue": "시가총액(억)",
    "localTradedAt": "기준시각",
}

DAILY_COLUMNS = {
    "localTradedAt": "날짜",
    "closePrice": "종가",
    "compareToPreviousClosePrice": "전일비",
    "fluctuationsRatio": "등락률(%)",
    "openPrice": "시가",
    "highPrice": "고가",
    "lowPrice": "저가",
}


def get_json(path: str, **params):
    res = requests.get(f"{API_BASE}/{path}", headers=HEADERS, params=params, timeout=10)
    res.raise_for_status()
    return res.json()


def fetch_index_summary() -> dict:
    """현재 지수값과 시가/고가/저가/52주 최고·최저 등 요약 정보"""
    basic = get_json("basic")
    summary = {
        "지수명": basic["stockName"],
        "현재가": basic["closePrice"],
        "전일비": basic["compareToPreviousClosePrice"],
        "등락률(%)": basic["fluctuationsRatio"],
        "장상태": basic["marketStatus"],
        "기준시각": basic["localTradedAt"],
    }
    for info in get_json("integration").get("totalInfos", []):
        summary[info["key"]] = info["value"]
    return summary


def fetch_constituents(limit: int = 200, log=print, should_stop=lambda: False) -> list[dict]:
    """편입종목을 시가총액 순으로 page=1,2,3... 넘기며 수집 (limit=0이면 API가 주는 전부)

    log: 진행 메시지를 받을 함수 (GUI에서는 시그널로 연결), should_stop: True를 돌려주면 중단
    """
    rows, seen, page = [], set(), 1
    while page <= MAX_PAGES and not should_stop():
        items = get_json("enrollStocks", page=page, pageSize=PAGE_SIZE)
        if not items:
            break
        for item in items:
            if item["itemCode"] in seen:  # 페이지 사이에 순위가 바뀌어 중복되는 경우 제외
                continue
            seen.add(item["itemCode"])
            rows.append({label: item.get(key, "") for key, label in STOCK_COLUMNS.items()})
        log(f"  {page}페이지: {len(items)}개 (누적 {len(rows)}개)")
        if len(items) < PAGE_SIZE or (limit and len(rows) >= limit):
            break
        page += 1
        time.sleep(0.2)

    if limit and len(rows) > limit:
        extra = rows[limit:]
        log(f"  API가 {len(rows)}개를 반환해 상위 {limit}개만 사용 "
              f"(제외: {', '.join(r['종목명'] for r in extra)}. 전부 받으려면 --limit 0)")
        rows = rows[:limit]
    return [{"순위": rank, **row} for rank, row in enumerate(rows, 1)]


def fetch_daily_prices(days: int) -> list[dict]:
    """최근 N거래일 지수 일별 시세"""
    items = get_json("price", page=1, pageSize=days)
    return [{label: item.get(key, "") for key, label in DAILY_COLUMNS.items()} for item in items]


def save_csv(path: str, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def save_excel(path: str, sheets: dict[str, list[dict]]) -> None:
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(name)
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))
    wb.save(path)


def main():
    parser = argparse.ArgumentParser(description="코스피200 지수/편입종목 크롤러")
    parser.add_argument("--out", default="kospi200.csv", help="저장 파일 (.csv 또는 .xlsx)")
    parser.add_argument("--days", type=int, default=0, help="함께 저장할 지수 일별 시세 일수")
    parser.add_argument("--limit", type=int, default=200, help="수집할 편입종목 수 (0이면 전부)")
    args = parser.parse_args()

    summary = fetch_index_summary()
    print(f"[{summary['지수명']}] {summary['현재가']} ({summary['전일비']}, {summary['등락률(%)']}%)"
          f"  {summary['장상태']} {summary['기준시각']}")
    for key in ("시가", "고가", "저가", "52주 최고", "52주 최저"):
        if key in summary:
            print(f"  {key}: {summary[key]}")

    print(f"\n편입종목 수집 중 (페이지당 {PAGE_SIZE}개)")
    stocks = fetch_constituents(args.limit)
    print(f"\n편입종목 {len(stocks)}개 수집 (상위 10개)")
    for s in stocks[:10]:
        print(f"  {s['순위']:>3}. {s['종목명']:<12} {s['현재가']:>10}  {s['등락률(%)']:>6}%  시총 {s['시가총액(억)']}억")

    daily = fetch_daily_prices(args.days) if args.days > 0 else []

    if args.out.lower().endswith(".xlsx"):
        sheets = {"지수요약": [summary], "편입종목": stocks}
        if daily:
            sheets["일별시세"] = daily
        save_excel(args.out, sheets)
        print(f"\n저장 완료: {args.out}")
    else:
        save_csv(args.out, stocks)
        print(f"\n저장 완료: {args.out}")
        if daily:
            daily_path = args.out.rsplit(".", 1)[0] + "_daily.csv"
            save_csv(daily_path, daily)
            print(f"저장 완료: {daily_path}")


if __name__ == "__main__":
    main()
