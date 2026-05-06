"""PTT (ptt.cc) keyword scraper — search posts and save to CSV."""

import csv
import re
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

# Cut points — ordered from most specific to least
_CUT = re.compile(
    r"\n※\s*(?:[a-zA-Z]\.|八卦板務|編輯|發信站)"  # board-rule blocks injected before --
    r"|\n--\s*(?:\n|$)",                           # PTT signature separator
    re.DOTALL,
)
_NOISE      = re.compile(r"(?:※|◆)[^\n]*\n?")    # stray ※ / ◆ lines after cut
_SEPARATORS = re.compile(r"[-─═=]{3,}")            # decorative separator lines
_URLS       = re.compile(r"https?://\S+")
_BLANKS     = re.compile(r"\n{3,}")


def _clean(text: str) -> str:
    m = _CUT.search(text)
    body = text[:m.start()] if m else text
    body = _NOISE.sub("", body)
    body = _SEPARATORS.sub("", body)
    body = _URLS.sub("", body)
    body = _BLANKS.sub("\n\n", body)
    return body.strip()


def _parse_time(raw: str) -> str:
    """Convert PTT time string to ISO-8601; return raw on failure."""
    try:
        return datetime.strptime(raw.strip(), "%a %b %d %H:%M:%S %Y").strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return raw.strip()


def fetch_post(client: httpx.Client, url: str) -> dict | None:
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

    content = _clean(main.get_text("\n"))
    return {
        "title":       title,
        "url":         url,
        "content":     content,
        "create_time": create_time,
        "author":      author,
    }


def search(
    keyword: str,
    board:   str = "Gossiping",
    count:   int = 0,           # 0 = no limit
    pages:   int = 10,          # safety cap on pages browsed
) -> list[dict]:
    """Search a PTT board for posts matching keyword; fetch full content of each."""
    url = f"{BASE_URL}/bbs/{board}/search?q={quote(keyword)}"
    posts: list[dict] = []

    with httpx.Client(headers=HEADERS, cookies=COOKIE, follow_redirects=True) as client:
        for _ in range(pages):
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for entry in soup.select("div.r-ent"):
                if count and len(posts) >= count:
                    break
                title_tag = entry.select_one("div.title a")
                if not title_tag:
                    continue
                post = fetch_post(client, BASE_URL + title_tag["href"])
                if post:
                    posts.append(post)
                    print(f"  [{len(posts)}] {post['title']}", file=sys.stderr)

            if count and len(posts) >= count:
                break

            prev = soup.select_one("a.btn.wide", string=lambda t: t and "上頁" in t)
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
            f, fieldnames=["title", "url", "content", "create_time", "author"]
        )
        writer.writeheader()
        writer.writerows(posts)

    return path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: python scraper.py <keyword> [board] [count] [pages]\n"
            "  keyword  search term (e.g. 蝦皮)\n"
            "  board    PTT board name  (default: Gossiping)\n"
            "  count    max records     (default: 0 = unlimited)\n"
            "  pages    max pages       (default: 10)",
            file=sys.stderr,
        )
        sys.exit(1)

    keyword = sys.argv[1]
    board   = sys.argv[2] if len(sys.argv) > 2 else "Gossiping"
    count   = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    pages   = int(sys.argv[4]) if len(sys.argv) > 4 else 10

    limit_str = str(count) if count else "unlimited"
    print(f"searching '{keyword}' in {board} (max {limit_str} records, {pages} pages)…", file=sys.stderr)

    posts = search(keyword, board, count, pages)
    path  = save_csv(posts, keyword)
    print(f"\nsaved {len(posts)} posts → {path}")
