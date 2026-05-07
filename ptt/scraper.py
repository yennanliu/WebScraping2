"""PTT (ptt.cc) keyword scraper — search posts and save to CSV."""

import csv
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

try:
    from ptt.clean import clean_content
except ImportError:
    from clean import clean_content  # running as script

BASE_URL = "https://www.ptt.cc"
COOKIE = {"over18": "1"}
OUTPUT_DIR = Path(__file__).parent / "output"


def _parse_time(raw: str) -> str:
    """Convert PTT time string to ISO-8601; return raw on failure."""
    try:
        return datetime.strptime(raw.strip(), "%a %b %d %H:%M:%S %Y").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return raw.strip()


def fetch_post(client: curl_requests.Session, url: str) -> dict | None:
    """Fetch a single post and return cleaned, structured data."""
    resp = client.get(url)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    main = soup.select_one("div#main-content")
    if not main:
        return None

    # meta-values appear in order: author, board, title, time
    meta = [s.text.strip() for s in main.select("span.article-meta-value")]
    author      = meta[0] if meta else ""
    title       = meta[2] if len(meta) > 2 else ""
    create_time = _parse_time(meta[3]) if len(meta) > 3 else ""

    for tag in main.select("div.article-metaline, div.article-metaline-right, div.push"):
        tag.decompose()

    content = clean_content(main.get_text("\n"))
    return {
        "title":       title,
        "url":         url,
        "create_time": create_time,
        "author":      author,
        "content":     content,
    }


def search(
    keyword: str,
    board:   str = "Gossiping",
    pages:   int = 1,   # how many result pages to walk back through
    count:   int = 0,   # hard cap on total records (0 = unlimited)
) -> list[dict]:
    """Search a PTT board for posts matching keyword; auto-paginate up to `pages` pages."""
    url = f"{BASE_URL}/bbs/{board}/search?q={quote(keyword)}"
    posts: list[dict] = []

    with curl_requests.Session(impersonate="chrome131") as client:
        client.cookies.update(COOKIE)
        for page_num in range(1, pages + 1):
            print(f"  page {page_num}/{pages} …", file=sys.stderr)
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
                    print(f"    [{len(posts)}] {post['title']}", file=sys.stderr)
                if count and len(posts) >= count:
                    return posts

            prev = next(
                (a for a in soup.select("a.btn.wide") if "上頁" in a.text), None
            )
            if not prev:
                break
            url = BASE_URL + prev["href"]

    return posts


def save_csv(posts: list[dict], keyword: str) -> Path:
    """Write posts to ptt/output/<keyword>_<timestamp>.csv and return the path."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{keyword.replace('/', '_')}_{ts}.csv"

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["title", "url", "create_time", "author", "content"]
        )
        writer.writeheader()
        writer.writerows(posts)

    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: python scraper.py <keyword> [board] [pages] [count]\n"
            "  keyword  search term (e.g. 蝦皮)\n"
            "  board    PTT board name  (default: Gossiping)\n"
            "  pages    pages to paginate through (default: 1)\n"
            "  count    max records, 0 = unlimited (default: 0)",
            file=sys.stderr,
        )
        sys.exit(1)

    keyword = sys.argv[1]
    board   = sys.argv[2] if len(sys.argv) > 2 else "Gossiping"
    pages   = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    count   = int(sys.argv[4]) if len(sys.argv) > 4 else 0

    limit_str = str(count) if count else "unlimited"
    print(f"searching '{keyword}' in {board} ({pages} page(s), max {limit_str} records)…", file=sys.stderr)

    posts = search(keyword, board, pages, count)
    path  = save_csv(posts, keyword)
    print(f"\nsaved {len(posts)} posts → {path}")
