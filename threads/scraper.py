"""Threads.net keyword search scraper — Playwright + network interception.

Strategy: intercept JSON responses from Threads' internal GraphQL endpoint as
the page scrolls, extract post data directly from the payloads.

Usage:
    uv run python threads/scraper.py <keyword>            # full scrape
    uv run python threads/scraper.py <keyword> --probe    # also save raw API responses
    uv run python threads/scraper.py <keyword> --headless # run without a visible browser
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

OUTPUT_DIR = Path(__file__).parent / "output"
BASE_URL = "https://www.threads.net"
MAX_IDLE_SCROLLS = 5   # stop after this many consecutive scrolls with no new posts
SCROLL_PAUSE_MS = 2500  # wait after each scroll for network responses to arrive


# ── JSON response parsing ─────────────────────────────────────────────────────


def _ts_to_iso(ts: int | float | None) -> str:
    if not ts:
        return ""
    try:
        return datetime.utcfromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return ""


def _find_edges(obj, depth: int = 0) -> list:
    """Recursively search a nested JSON structure for the first non-empty 'edges' list."""
    if depth > 12 or not isinstance(obj, (dict, list)):
        return []
    if isinstance(obj, list):
        for item in obj:
            result = _find_edges(item, depth + 1)
            if result:
                return result
        return []
    # dict: check this level first, then recurse into values
    if "edges" in obj and isinstance(obj["edges"], list) and obj["edges"]:
        return obj["edges"]
    for v in obj.values():
        result = _find_edges(v, depth + 1)
        if result:
            return result
    return []


def _extract_posts(payload: dict, seen_ids: set) -> list[dict]:
    """
    Walk a Threads GraphQL response and return new post records.
    Updates seen_ids in-place to deduplicate across multiple responses.

    Threads wraps posts in thread_items inside edge nodes:
      data -> ... -> edges[] -> node -> thread_items[] -> post -> {pk, user, caption, ...}
    """
    posts = []
    edges = _find_edges(payload)

    for edge in edges:
        node = edge.get("node", edge) if isinstance(edge, dict) else edge
        if not isinstance(node, dict):
            continue

        # each node may contain multiple posts (OP + replies in a thread)
        thread_items = node.get("thread_items") or [node]

        for item in thread_items:
            post = item.get("post", item) if isinstance(item, dict) else item
            if not isinstance(post, dict):
                continue

            post_id = str(post.get("pk") or post.get("id") or "")
            if not post_id or post_id in seen_ids:
                continue

            user = post.get("user") or {}
            caption = post.get("caption") or {}
            text = (
                caption.get("text", "")
                if isinstance(caption, dict)
                else str(caption)
            )
            reply_info = post.get("text_post_app_info") or {}
            username = user.get("username", "")

            seen_ids.add(post_id)
            posts.append({
                "post_id": post_id,
                "author": username,
                "text": text,
                "created_at": _ts_to_iso(post.get("taken_at")),
                "like_count": post.get("like_count", 0),
                "reply_count": reply_info.get("reply_count", post.get("reply_count", 0)),
                "url": f"{BASE_URL}/@{username}/post/{post_id}",
            })

    return posts


# ── browser / scrape logic ────────────────────────────────────────────────────


def search(keyword: str, headless: bool = False, probe: bool = False) -> list[dict]:
    """
    Open Threads search for `keyword`, scroll until no new posts load, and
    return all collected posts.

    headless=False by default — visible browser is less likely to be blocked.
    probe=True additionally saves all raw API responses for field inspection.
    """
    from playwright.sync_api import sync_playwright  # lazy import — only needed at runtime

    OUTPUT_DIR.mkdir(exist_ok=True)
    search_url = f"{BASE_URL}/search?q={quote(keyword)}&serp_type=default"

    all_posts: list[dict] = []
    seen_ids: set[str] = set()
    raw_responses: list[dict] = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="zh-TW",
        )
        page = context.new_page()

        def on_response(response):
            if "threads.net" not in response.url:
                return
            if "json" not in response.headers.get("content-type", ""):
                return
            try:
                body = response.json()
            except Exception:
                return

            if probe:
                raw_responses.append({"url": response.url, "body": body})

            new = _extract_posts(body, seen_ids)
            if new:
                all_posts.extend(new)
                print(f"  +{len(new)} posts  (total {len(all_posts)})", flush=True)

        page.on("response", on_response)

        print(f"opening: {search_url}")
        page.goto(search_url, wait_until="networkidle", timeout=30_000)

        idle = 0
        while idle < MAX_IDLE_SCROLLS:
            prev_count = len(all_posts)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(SCROLL_PAUSE_MS)
            if len(all_posts) == prev_count:
                idle += 1
                print(f"  no new posts ({idle}/{MAX_IDLE_SCROLLS} idle scrolls)", flush=True)
            else:
                idle = 0

        browser.close()

    if probe:
        probe_path = OUTPUT_DIR / f"probe_{keyword.replace('/', '_')}.json"
        probe_path.write_text(
            json.dumps(raw_responses, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nprobe data saved → {probe_path}")

    return all_posts


def save_json(posts: list[dict], keyword: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"{keyword.replace('/', '_')}_{ts}.json"
    path.write_text(json.dumps(posts, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


# ── CLI ───────────────────────────────────────────────────────────────────────


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "usage: uv run python threads/scraper.py <keyword> [--probe] [--headless]\n"
            "  --probe     save raw API responses to output/probe_<keyword>.json\n"
            "  --headless  run browser without a visible window",
            file=sys.stderr,
        )
        sys.exit(1)

    _keyword = sys.argv[1]
    _probe = "--probe" in sys.argv
    _headless = "--headless" in sys.argv

    _posts = search(_keyword, headless=_headless, probe=_probe)

    if not _posts:
        print(
            "\nNo posts extracted.\n"
            "Try running with --probe to inspect raw API responses:\n"
            f"  uv run python threads/scraper.py {_keyword} --probe"
        )
        sys.exit(0)

    _path = save_json(_posts, _keyword)
    print(f"\nsaved {len(_posts)} posts → {_path}")
