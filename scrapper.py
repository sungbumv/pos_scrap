import requests
from bs4 import BeautifulSoup
import os
import time
import re
from urllib.parse import quote
from datetime import datetime

# 검색할 키워드와 옵션
QUERY = "POS"
PAGES = 5             # 검색 결과 페이지 개수 (필요시 조정)
RESULTS_PER_PAGE = 10  # 페이지당 기사 수
BASE_DIR = "articles"  # 최상위 저장 폴더
# 실행 날짜 기반 서브폴더
DATE_STR = datetime.now().strftime("%Y%m%d")
OUTPUT_DIR = os.path.join(BASE_DIR, DATE_STR)

# 헤더 설정: 봇 차단 회피용
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/112.0.0.0 Safari/537.36"
    )
}


def get_search_urls(query, pages):
    urls = []
    base = "https://search.naver.com/search.naver"
    for page in range(1, pages + 1):
        start = (page - 1) * RESULTS_PER_PAGE + 1
        q = quote(query)
        url = f"{base}?where=news&query={q}&start={start}"
        urls.append(url)
    return urls


def parse_search_results(url):
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    news_list = soup.find('ul', class_='list_news')
    if news_list:
        candidates = news_list.find_all('a', href=True)
    else:
        candidates = soup.find_all('a', href=True)

    links = []
    for a in candidates:
        href = a['href']
        txt = a.get_text(strip=True)
        if href.startswith(('http://', 'https://')) and len(txt) > 20:
            links.append(href)
    return list(dict.fromkeys(links))


def fetch_article(url):
    r = requests.get(url, headers=HEADERS, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')

    # 제목 추출
    title = None
    og = soup.find('meta', property='og:title')
    if og and og.get('content'):
        title = og['content'].strip()
    if not title:
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        else:
            title = url

    # 본문 셀렉터 시도
    selectors = [
        ('div', {'id': 'articleBodyContents'}),
        ('div', {'class': 'news_end'}),
        ('div', {'class': 'article-body'}),
        ('div', {'class': 'article-content'})
    ]
    body = None
    for tag, attrs in selectors:
        body = soup.find(tag, attrs=attrs)
        if body:
            break

    if body:
        paragraphs = body.find_all('p')
    else:
        paragraphs = soup.find_all('p')

    text = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
    return title, text


def sanitize_filename(name):
    return re.sub(r'[\\/:"*?<>|]+', '_', name)


def save_article(title, text, url):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    safe = sanitize_filename(title)[:50]
    path = os.path.join(OUTPUT_DIR, f"{safe}.txt")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(f"URL: {url}\n")
        f.write(f"Title: {title}\n\n")
        f.write(text)
    print(f"Saved: {path}")


def main():
    print(f"▶▶▶ Scraping POS articles on {DATE_STR}")
    for url in get_search_urls(QUERY, PAGES):
        print(f"→ 검색 페이지 요청: {url}")
        links = parse_search_results(url)
        print(f"  찾은 링크 개수: {len(links)}")
        for link in links:
            print(f"    ▶ 링크 처리: {link}")
            try:
                title, text = fetch_article(link)
                if QUERY in text:
                    save_article(title, text, link)
                else:
                    print(f"Skipped (no '{QUERY}'): {title}")
                time.sleep(1)
            except Exception as e:
                print(f"Error fetching {link}: {e}")

if __name__ == '__main__':
    main()