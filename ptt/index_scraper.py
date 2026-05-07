"""PTT index-based scraper — Two-Phase strategy with resume support.

Phase 1  (serial)    crawl index pages, collect matched post URLs → progress file
Phase 2  (parallel)  fetch post content with thread pool, append to JSONL → progress file

Output format: newline-delimited JSON (.jsonl) — one post object per line.
Resume: just re-run the same command; the progress file is picked up automatically.
"""

import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

try:
    from ptt.clean import clean_content
except ImportError:
    from clean import clean_content  # running as script

BASE_URL = "https://www.ptt.cc"
COOKIE = {"over18": "1"}
OUTPUT_DIR = Path(__file__).parent / "output"
PROGRESS_DIR = OUTPUT_DIR / "progress"
CRAWL_DELAY = 0.05  # seconds between index-page requests (be polite)

def _parse_time(raw: str) -> str:
    try:
        return datetime.strptime(raw.strip(), "%a %b %d %H:%M:%S %Y").strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    except ValueError:
        return raw.strip()


def _parse_index_date(date_str: str, today: date) -> date | None:
    """Parse PTT index page date ('M/DD') → date, inferring year from today."""
    try:
        month, day = map(int, date_str.strip().split("/"))
        # try current year first, then previous year
        for year in (today.year, today.year - 1):
            try:
                d = date(year, month, day)
                if d <= today:
                    return d
            except ValueError:
                continue
    except (ValueError, AttributeError):
        pass
    return None


# ── thread-local HTTP session (one curl handle per worker thread) ─────────────

_local = threading.local()


def _client() -> curl_requests.Session:
    if not hasattr(_local, "http"):
        s = curl_requests.Session(impersonate="chrome131")
        s.cookies.update(COOKIE)
        _local.http = s
    return _local.http


# ── PTT fetchers ──────────────────────────────────────────────────────────────


@dataclass
class PostMeta:
    title: str
    url: str
    author: str = ""
    date: date | None = None


def get_max_index(board: str) -> int:
    """Return current highest index-page number for a board."""
    resp = _client().get(f"{BASE_URL}/bbs/{board}/index.html")
    resp.raise_for_status()
    # after redirect, the URL itself contains the max index
    # index.html serves the latest page directly (no redirect)
    # the 上頁 link points to max-1, so max = that number + 1
    soup = BeautifulSoup(resp.text, "lxml")
    prev = next(
        (a for a in soup.select("a.btn.wide") if "上頁" in a.text),
        None,
    )
    if not prev:
        raise RuntimeError(f"Cannot determine max index for board '{board}'")
    return int(prev["href"].rsplit("index", 1)[1].replace(".html", "")) + 1


def fetch_index_page(board: str, n: int) -> list[PostMeta]:
    """Return PostMeta list for index page N; skips deleted posts."""
    resp = _client().get(f"{BASE_URL}/bbs/{board}/index{n}.html")
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")
    today = date.today()
    out = []
    for entry in soup.select("div.r-ent"):
        a = entry.select_one("div.title a")
        if not a:
            continue  # deleted post
        author_tag = entry.select_one("div.author")
        date_tag = entry.select_one("div.date")
        post_date = _parse_index_date(date_tag.text, today) if date_tag else None
        out.append(
            PostMeta(
                title=a.text.strip(),
                url=BASE_URL + a["href"],
                author=author_tag.text.strip() if author_tag else "",
                date=post_date,
            )
        )
    return out


def fetch_post(url: str) -> dict | None:
    """Fetch a single post and return structured data, or None on failure."""
    try:
        resp = _client().get(url)
        resp.raise_for_status()
    except Exception:
        return None
    soup = BeautifulSoup(resp.text, "lxml")
    main = soup.select_one("div#main-content")
    if not main:
        return None
    meta = [s.text.strip() for s in main.select("span.article-meta-value")]
    author = meta[0] if meta else ""
    title = meta[2] if len(meta) > 2 else ""
    create_time = _parse_time(meta[3]) if len(meta) > 3 else ""
    for tag in main.select(
        "div.article-metaline, div.article-metaline-right, div.push"
    ):
        tag.decompose()
    return {
        "title": title,
        "url": url,
        "create_time": create_time,
        "author": author,
        "content": clean_content(main.get_text("\n")),
    }


# ── progress file ─────────────────────────────────────────────────────────────


def _progress_path(board: str, keyword: str) -> Path:
    return PROGRESS_DIR / f".{board}_{keyword.replace('/', '_')}_progress.json"


def _load(board: str, keyword: str) -> dict | None:
    p = _progress_path(board, keyword)
    if not p.exists():
        return None
    state = json.loads(p.read_text(encoding="utf-8"))
    # migrate legacy "csv_path" key
    if "csv_path" in state and "output_path" not in state:
        state["output_path"] = state.pop("csv_path").replace(".csv", ".json")
        _save(state)
    # migrate .jsonl → .json
    elif state.get("output_path", "").endswith(".jsonl"):
        state["output_path"] = state["output_path"].replace(".jsonl", ".json")
        _save(state)
    return state


def _save(state: dict) -> None:
    _progress_path(state["board"], state["keyword"]).write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ── phase 1: index crawl ──────────────────────────────────────────────────────


def _phase1(state: dict) -> None:
    board, keyword = state["board"], state["keyword"]
    target = state["target_page"]
    matched = state["matched_urls"]
    seen = set(matched)
    n = state["next_page"]
    total = state["max_page"] - target + 1
    cutoff = date.today() - timedelta(days=365)

    print(f"\nPhase 1/2 — scanning index pages  [{board}]  index{n} → index{target}")
    print(f"  date filter: posts on or after {cutoff}")

    while n >= target:
        try:
            metas = fetch_index_page(board, n)
        except Exception as e:
            print(f"\n  [WARN] index{n} failed: {e}, skipping")
            n -= 1
            continue

        for m in metas:
            if m.date is not None and m.date < cutoff:
                continue
            if keyword in m.title and m.url not in seen:
                seen.add(m.url)
                matched.append(m.url)

        scanned = state["max_page"] - n + 1
        print(
            f"  [{scanned:>5}/{total}]  index{n:<6}  {len(matched)} matches",
            end="\r",
            flush=True,
        )

        n -= 1
        state["next_page"] = n
        state["matched_urls"] = matched
        _save(state)
        time.sleep(CRAWL_DELAY)

        # stop once the oldest post on this page is beyond the cutoff
        dated = [m.date for m in metas if m.date is not None]
        if dated and min(dated) < cutoff:
            break

    state["phase1_done"] = True
    _save(state)
    print(f"\nPhase 1 done — {len(matched)} matched URLs found\n")


# ── phase 2: parallel post fetch ──────────────────────────────────────────────


def _json_has_data(path: Path) -> bool:
    """Return True if the JSON file contains a non-empty array."""
    if not path.exists():
        return False
    try:
        with path.open("r", encoding="utf-8") as f:
            return len(json.load(f)) > 0
    except Exception:
        return False


def _phase2(state: dict, workers: int) -> None:
    out_path = Path(state["output_path"])
    fetched = set(state["fetched_urls"])

    # output missing or empty despite progress claiming work is done — re-fetch
    if fetched and not _json_has_data(out_path):
        print("  [WARN] output missing or empty — resetting, will re-fetch all records")
        fetched = set()
        state["fetched_urls"] = []
        _save(state)

    pending = [u for u in state["matched_urls"] if u not in fetched]
    total = len(state["matched_urls"])
    done_count = len(fetched)

    print(f"Phase 2/2 — fetching post content  [{workers} workers]")
    print(f"  {len(pending)} pending  |  {done_count} already done  |  {total} total")

    if not pending:
        print(f"\nPhase 2 done — {out_path}")
        return

    cutoff = datetime.now() - timedelta(days=365)
    lock = threading.Lock()
    new_posts: list[dict] = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_post, url): url for url in pending}

        for future in as_completed(futures):
            url = futures[future]
            post = future.result()

            with lock:
                done_count += 1
                fetched.add(url)
                if post:
                    try:
                        post_dt = datetime.strptime(post["create_time"], "%Y-%m-%d %H:%M:%S")
                        if post_dt >= cutoff:
                            new_posts.append(post)
                        else:
                            post = None  # too old — suppress label
                    except ValueError:
                        new_posts.append(post)  # unparseable date, keep it
                state["fetched_urls"] = list(fetched)
                _save(state)

                label = post["title"][:60] if post else "(too old / failed)"
                print(f"  [{done_count:>5}/{total}]  {label}")

    # merge with any previously written data, then write the full array
    existing: list[dict] = []
    if out_path.exists():
        try:
            with out_path.open("r", encoding="utf-8") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, ValueError):
            existing = []

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(existing + new_posts, f, ensure_ascii=False, indent=2)

    print(f"\nPhase 2 done — {out_path}")


# ── public entry ──────────────────────────────────────────────────────────────


def crawl(
    board: str = "Gossiping",
    keyword: str = "蝦皮",
    pages: int = 200,
    workers: int = 8,
) -> Path:
    """
    Crawl `pages` index pages of `board`, collect posts whose title contains
    `keyword`, fetch their content, and save to JSONL.

    Re-running the same call resumes from the saved progress file.
    """
    OUTPUT_DIR.mkdir(exist_ok=True)
    PROGRESS_DIR.mkdir(exist_ok=True)
    state = _load(board, keyword)

    if state is None:
        max_page = get_max_index(board)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        state = {
            "board": board,
            "keyword": keyword,
            "max_page": max_page,
            "target_page": max(1, max_page - pages + 1),
            "next_page": max_page,
            "matched_urls": [],
            "fetched_urls": [],
            "output_path": str(
                OUTPUT_DIR / f"{keyword.replace('/', '_')}_{board}_{ts}.json"
            ),
            "phase1_done": False,
        }
        _save(state)
        print(f"New crawl — {board} / '{keyword}'")
        print(f"  index range: {max_page} → {state['target_page']}  ({pages} pages)")
    else:
        p1 = "done" if state["phase1_done"] else f"next=index{state['next_page']}"
        print(f"Resuming — {board} / '{keyword}'")
        print(
            f"  phase 1: {p1}  |  matched: {len(state['matched_urls'])}  |  fetched: {len(state['fetched_urls'])}"
        )

    if not state["phase1_done"]:
        _phase1(state)

    _phase2(state, workers)
    return Path(state["output_path"])


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: python index_scraper.py <keyword> [board] [pages] [workers]\n"
            "  keyword   search term (e.g. 蝦皮)\n"
            "  board     PTT board name      (default: Gossiping)\n"
            "  pages     index pages to scan (default: 200)\n"
            "  workers   parallel fetchers   (default: 8)\n\n"
            "Re-run the same command to resume an interrupted crawl.",
            file=sys.stderr,
        )
        sys.exit(1)

    keyword = sys.argv[1]
    board = sys.argv[2] if len(sys.argv) > 2 else "Gossiping"
    pages = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    workers = int(sys.argv[4]) if len(sys.argv) > 4 else 8

    path = crawl(board, keyword, pages, workers)
    print(f"\nsaved → {path}")
