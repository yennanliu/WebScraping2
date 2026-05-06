"""PTT (ptt.cc) board scraper."""

import httpx
from bs4 import BeautifulSoup

BASE_URL = "https://www.ptt.cc"
COOKIE = {"over18": "1"}  # bypass age gate


def fetch_board(board: str, pages: int = 1) -> list[dict]:
    """Return posts from a PTT board across `pages` pages."""
    posts = []
    url = f"{BASE_URL}/bbs/{board}/index.html"

    with httpx.Client(cookies=COOKIE, follow_redirects=True) as client:
        for _ in range(pages):
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")

            for entry in soup.select("div.r-ent"):
                title_tag = entry.select_one("div.title a")
                if not title_tag:
                    continue
                posts.append({
                    "title": title_tag.text.strip(),
                    "href": BASE_URL + title_tag["href"],
                    "author": entry.select_one("div.author").text.strip(),
                    "date": entry.select_one("div.date").text.strip(),
                    "push": entry.select_one("div.nrec").text.strip() or "0",
                })

            prev_tag = soup.select_one("a.btn.wide", string=lambda t: t and "上頁" in t)
            if not prev_tag:
                break
            url = BASE_URL + prev_tag["href"]

    return posts


if __name__ == "__main__":
    import json
    import sys

    board = sys.argv[1] if len(sys.argv) > 1 else "Gossiping"
    pages = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    results = fetch_board(board, pages)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n{len(results)} posts fetched from {board}", file=sys.stderr)
