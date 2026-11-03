"""
네이버 검색 결과에서 뉴스 기사를 찾아 본문까지 크롤링하는 스크립트 (requests + BeautifulSoup4)

사용법:
    pip install requests beautifulsoup4 openpyxl
    python naver_news_crawler.py                 # 기본 URL(반도체 통합검색) 사용
    python naver_news_crawler.py --news          # 뉴스 탭(where=news)으로 더 많은 기사 수집
    python naver_news_crawler.py --limit 5 --out result.csv
    python naver_news_crawler.py --out result.xlsx   # 엑셀 파일로 저장

참고:
    네이버 검색 결과의 CSS 클래스명은 난독화되어 자주 바뀌므로,
    비교적 안정적인 data-heatmap-target 속성(.tit=제목, .body=요약, .nav=네이버뉴스 링크)을 기준으로 파싱합니다.
"""

import argparse
import csv
import time
from urllib.parse import parse_qs, urlencode, urlparse

import requests
from bs4 import BeautifulSoup

SEARCH_URL = (
    "https://search.naver.com/search.naver?where=nexearch&sm=top_hty&fbm=0&ie=utf8"
    "&query=%EB%B0%98%EB%8F%84%EC%B2%B4&ackey=iennk90y"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://www.naver.com/",
}


def get_soup(url: str) -> BeautifulSoup:
    res = requests.get(url, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def to_news_tab_url(url: str) -> str:
    """통합검색 URL의 검색어를 그대로 사용해 뉴스 탭 URL로 변환"""
    query = parse_qs(urlparse(url).query).get("query", [""])[0]
    return "https://search.naver.com/search.naver?" + urlencode({"where": "news", "query": query})


def find_item_container(title_tag):
    """제목 링크 하나만 포함하는 가장 큰 상위 요소 = 기사 한 건의 영역"""
    item = title_tag
    while item.parent is not None:
        if len(item.parent.select('a[data-heatmap-target=".tit"]')) > 1:
            break
        item = item.parent
    return item


def parse_search_results(soup: BeautifulSoup) -> list[dict]:
    """검색 결과 페이지에서 기사 목록(제목, 원문 링크, 네이버뉴스 링크, 요약)을 추출"""
    articles = []
    for title_tag in soup.select('a[data-heatmap-target=".tit"]'):
        item = find_item_container(title_tag)
        body_tag = item.select_one('[data-heatmap-target=".body"]')
        naver_tag = item.select_one('a[data-heatmap-target=".nav"]')

        articles.append({
            "title": title_tag.get_text(strip=True),
            "url": title_tag.get("href", ""),
            "naver_url": naver_tag.get("href", "") if naver_tag else "",
            "summary": body_tag.get_text(" ", strip=True) if body_tag else "",
        })
    return articles


def parse_naver_article(url: str) -> dict:
    """네이버뉴스(n.news.naver.com) 기사 페이지에서 언론사, 날짜, 본문 추출"""
    soup = get_soup(url)

    title = soup.select_one("#title_area")
    press = soup.select_one(".media_end_head_top_logo img")
    date = soup.select_one("span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME")
    body = soup.select_one("#dic_area")

    if body:
        # 사진 설명, 스크립트 등 본문이 아닌 요소 제거
        for tag in body.select("script, style, .end_photo_org, .img_desc, em.img_desc"):
            tag.decompose()

    return {
        "title": title.get_text(strip=True) if title else "",
        "press": press.get("alt", "") if press else "",
        "date": date.get("data-date-time", "") if date else "",
        "content": body.get_text("\n", strip=True) if body else "",
    }


def parse_generic_article(url: str) -> dict:
    """네이버뉴스 링크가 없는 기사: 언론사 원문에서 <p> 태그 위주로 본문 추정"""
    soup = get_soup(url)
    container = soup.select_one("article") or soup.body or soup
    paragraphs = [p.get_text(" ", strip=True) for p in container.select("p")]
    paragraphs = [p for p in paragraphs if len(p) > 30]

    og_site = soup.select_one('meta[property="og:site_name"]')
    return {
        "title": "",
        "press": og_site.get("content", "") if og_site else "",
        "date": "",
        "content": "\n".join(paragraphs),
    }


def crawl(url: str, limit: int, delay: float) -> list[dict]:
    soup = get_soup(url)
    articles = parse_search_results(soup)[:limit]
    print(f"검색 결과에서 기사 {len(articles)}건 발견\n")

    for i, article in enumerate(articles, 1):
        try:
            if article["naver_url"]:
                detail = parse_naver_article(article["naver_url"])
            else:
                detail = parse_generic_article(article["url"])
        except requests.RequestException as e:
            print(f"[{i}] 본문 수집 실패: {e}")
            detail = {"title": "", "press": "", "date": "", "content": ""}

        article["title"] = detail["title"] or article["title"]
        article["press"] = detail["press"]
        article["date"] = detail["date"]
        article["content"] = detail["content"] or article["summary"]

        print(f"[{i}] {article['title']}")
        print(f"    언론사: {article['press']} | 날짜: {article['date']}")
        print(f"    링크: {article['naver_url'] or article['url']}")
        print(f"    본문: {article['content'][:150]}...\n")

        time.sleep(delay)  # 서버 부하를 줄이기 위한 요청 간격

    return articles


def save_csv(articles: list[dict], path: str) -> None:
    fields = ["title", "press", "date", "url", "naver_url", "summary", "content"]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # 엑셀 한글 깨짐 방지
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(articles)
    print(f"CSV 저장 완료: {path} ({len(articles)}건)")


EXCEL_HEADERS = {
    "title": "제목",
    "press": "언론사",
    "date": "날짜",
    "url": "원문 링크",
    "naver_url": "네이버뉴스 링크",
    "summary": "요약",
    "content": "본문",
}
EXCEL_WIDTHS = [50, 14, 20, 40, 40, 50, 80]


def save_excel(articles: list[dict], path: str) -> None:
    from openpyxl import Workbook
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = "뉴스"
    ws.append(list(EXCEL_HEADERS.values()))

    for article in articles:
        row = []
        for key in EXCEL_HEADERS:
            value = ILLEGAL_CHARACTERS_RE.sub("", str(article.get(key, "")))  # 엑셀에서 허용하지 않는 제어문자 제거
            row.append(value[:32767])  # 엑셀 셀 최대 글자 수
        ws.append(row)

    # 헤더 스타일
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="03C75A")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # 열 너비, 줄바꿈, 링크 하이퍼링크 처리
    for col, width in enumerate(EXCEL_WIDTHS, 1):
        ws.column_dimensions[get_column_letter(col)].width = width
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=cell.column >= 6)
            if cell.column in (4, 5) and cell.value:
                cell.hyperlink = cell.value
                cell.style = "Hyperlink"

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    wb.save(path)
    print(f"엑셀 저장 완료: {path} ({len(articles)}건)")


def save_file(articles: list[dict], path: str) -> None:
    """확장자에 따라 엑셀(.xlsx) 또는 CSV로 저장"""
    if path.lower().endswith(".xlsx"):
        save_excel(articles, path)
    else:
        save_csv(articles, path)


def main():
    parser = argparse.ArgumentParser(description="네이버 뉴스 검색 결과 크롤러")
    parser.add_argument("--url", default=SEARCH_URL, help="네이버 검색 URL")
    parser.add_argument("--news", action="store_true", help="뉴스 탭(where=news)에서 수집")
    parser.add_argument("--limit", type=int, default=10, help="수집할 최대 기사 수")
    parser.add_argument("--delay", type=float, default=0.5, help="요청 간 대기 시간(초)")
    parser.add_argument("--out", default="naver_news.csv", help="저장할 파일 경로 (.csv 또는 .xlsx)")
    args = parser.parse_args()

    url = to_news_tab_url(args.url) if args.news else args.url
    articles = crawl(url, args.limit, args.delay)
    if articles:
        save_file(articles, args.out)


if __name__ == "__main__":
    main()
