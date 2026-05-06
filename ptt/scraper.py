"""PTT (ptt.cc) keyword scraper — search posts and save to CSV."""

import csv
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.ptt.cc"
COOKIE = {"over18": "1"}
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
}
OUTPUT_DIR = Path(__file__).parent / "output"


def fetch_post(client: httpx.Client, url: str) -> dict | None:
    """Fetch a single post page and return structured data."""
    resp = client.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    main = soup.select_one("div#main-content")
    if not main:
        return None

    meta = [s.text.strip() for s in main.select("span.article-meta-value")]
    author = meta[0] if meta else ""
    title  = meta[2] if len(meta) > 2 else ""
    time   = meta[3] if len(meta) > 3 else ""

    for tag in main.select("div.article-metaline, div.article-metaline-right, div.push"):
        tag.decompose()

    content = main.get_text("\n", strip=True)
    return {"title": title, "url": url, "content": content, "time": time, "author": author}


def search(keyword: str, board: str = "Gossiping", pages: int = 1) -> list[dict]:
    """Search a PTT board for posts matching keyword; fetch full content of each."""
    url = f"{BASE_URL}/bbs/{board}/search?q={quote(keyword)}"
    posts = []

    with httpx.Client(headers=HEADERS, cookies=COOKIE, follow_redirects=True) as client:
        for _ in range(pages):
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for entry in soup.select("div.r-ent"):
                title_tag = entry.select_one("div.title a")
                if not title_tag:
                    continue
                post = fetch_post(client, BASE_URL + title_tag["href"])
                if post:
                    posts.append(post)
                    print(f"  fetched: {post['title']}", file=sys.stderr)

            prev = soup.select_one("a.btn.wide", string=lambda t: t and "上頁" in t)
            if not prev:
                break
            url = BASE_URL + prev["href"]

    return posts


def save_csv(posts: list[dict], keyword: str) -> Path:
    """Write posts to ptt/output/<keyword>_<timestamp>.csv and return the path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{keyword.replace('/', '_')}_{ts}.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["title", "url", "content", "time", "author"])
        writer.writeheader()
        writer.writerows(posts)

    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python scraper.py <keyword> [board] [pages]", file=sys.stderr)
        sys.exit(1)

    keyword = sys.argv[1]
    board   = sys.argv[2] if len(sys.argv) > 2 else "Gossiping"
    pages   = int(sys.argv[3]) if len(sys.argv) > 3 else 1

    print(f"searching '{keyword}' in {board} ({pages} page(s))…", file=sys.stderr)
    posts = search(keyword, board, pages)
    path  = save_csv(posts, keyword)
    print(f"\nsaved {len(posts)} posts → {path}")
