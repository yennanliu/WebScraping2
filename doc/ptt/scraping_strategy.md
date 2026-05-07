# PTT Index-Based Scraping — Strategy Comparison

## Background

PTT boards expose a deterministic index structure:

```
https://www.ptt.cc/bbs/{board}/index.html       ← newest (redirects to current max)
https://www.ptt.cc/bbs/{board}/index{N}.html    ← page N (20 posts per page)
https://www.ptt.cc/bbs/{board}/index1.html      ← oldest
```

Each index page lists ~20 posts (title, author, date, URL). Fetching post content
is a separate request per post. This two-level structure — **index pages → post pages** —
drives all strategy trade-offs below.

**Why index-based over search-based**

| | search (`?q=keyword`) | index crawl |
|---|---|---|
| Coverage | PTT's own index, ~600–800 posts cap | full archive, unlimited |
| Speed | fast (targeted) | slower (crawl all pages) |
| Keyword filtering | server-side | local (title match) |
| Date range | not supported | supported (parse date from index) |

---

## Anatomy of a crawl job

```
Step 1  Find max index N  →  GET /bbs/{board}/index.html
Step 2  Crawl index pages →  GET /bbs/{board}/index{N}.html  (20 titles/page)
Step 3  Filter            →  keyword in title AND date in range
Step 4  Fetch posts       →  GET each matched post URL
Step 5  Save              →  write CSV
```

Steps 2 and 4 are where strategies diverge.

---

## Strategy A — Sequential (simple loop)

```
for page N down to 1:
    fetch index page  →  filter titles  →  fetch each matched post immediately
```

**Flow:**

```
index[N] → post1 → post2 → post3
index[N-1] → post4 → post5
...
```

**Code sketch:**

```python
def crawl(board, keyword, start, end, client):
    for n in range(start, end - 1, -1):
        metas = fetch_index_page(client, board, n)
        if past_date_range(metas):
            break
        for m in metas:
            if keyword in m.title:
                post = fetch_post(client, m.url)
                yield post
```

| | |
|---|---|
| Pros | simplest code; results stream immediately; easy to stop early |
| Cons | fully serial — one slow response blocks everything; ~1–2 req/s |
| Effort | low |
| Best for | quick one-off runs, debugging, small boards |

---

## Strategy B — Two-Phase (BFS-style) ✓ recommended

Separate **discovery** from **fetching**. Crawl all index pages first (cheap, fast),
collect matched URLs, then bulk-fetch post content in parallel.

```
Phase 1 (serial):    index[N] → index[N-1] → ... → collect [url1, url2, ...]
Phase 2 (parallel):  ThreadPoolExecutor fetches all post URLs concurrently
```

**Code sketch:**

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def crawl(board, keyword, start, end, workers=8):
    # Phase 1 — fast, index pages are tiny
    matched_urls = []
    with httpx.Client(...) as client:
        for n in range(start, end - 1, -1):
            metas = fetch_index_page(client, board, n)
            if past_date_range(metas):
                break
            matched_urls += [m.url for m in metas if keyword in m.title]

    # Phase 2 — parallel post fetching
    posts = []
    with httpx.Client(...) as client:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(fetch_post, client, url): url
                       for url in matched_urls}
            for f in as_completed(futures):
                post = f.result()
                if post:
                    posts.append(post)
    return posts
```

| | |
|---|---|
| Pros | phase 2 is trivially parallelizable; clean separation of concerns; predictable |
| Cons | phase 1 must finish before phase 2 starts; holds all URLs in memory |
| Effort | low-medium |
| Best for | **standard use** — moderate boards, date-ranged keyword searches |

**Practical throughput:**  
Phase 1: ~20 index pages/sec (tiny payloads).  
Phase 2: with 8 workers, ~8 posts/sec → 10,000 posts ≈ 20 minutes.

---

## Strategy C — Pipeline (DFS-style, producer + consumer)

Index page crawling and post fetching run **concurrently** via a shared queue.
One thread produces URLs; N worker threads consume and fetch post content.

```
Producer thread:  index[N] → queue → index[N-1] → queue → ...
Worker threads:   queue → fetch post → save
```

**Code sketch:**

```python
from queue import Queue
from threading import Thread

def crawl(board, keyword, start, end, workers=8):
    q = Queue(maxsize=200)
    results = []

    def producer():
        with httpx.Client(...) as client:
            for n in range(start, end - 1, -1):
                metas = fetch_index_page(client, board, n)
                if past_date_range(metas):
                    break
                for m in metas:
                    if keyword in m.title:
                        q.put(m.url)
        for _ in range(workers):
            q.put(None)  # sentinel

    def worker():
        with httpx.Client(...) as client:
            while True:
                url = q.get()
                if url is None:
                    break
                post = fetch_post(client, url)
                if post:
                    results.append(post)

    t = Thread(target=producer)
    t.start()
    threads = [Thread(target=worker) for _ in range(workers)]
    for w in threads:
        w.start()
    t.join()
    for w in threads:
        w.join()

    return results
```

| | |
|---|---|
| Pros | maximum overlap — no idle time waiting for phase 1 to finish; first results appear fast |
| Cons | more moving parts (queue, sentinels, thread coordination); harder to debug |
| Effort | medium |
| Best for | very large boards where phase 1 itself takes minutes (e.g., full Gossiping history) |

---

## Comparison table

| | A — Sequential | B — Two-Phase | C — Pipeline |
|---|---|---|---|
| Complexity | low | low-medium | medium |
| Throughput | ~1–2 req/s | ~8–16 req/s (phase 2) | ~8–16 req/s (overlapped) |
| First result | immediate | after phase 1 | fast (overlap) |
| Resumable | easy | easy (save URL list) | harder |
| Memory | minimal | holds all URLs | queue-bounded |
| Debug ease | easy | easy | harder |
| Recommended for | dev/debug | **production default** | very large jobs |

---

## Recommended architecture

For local, single-node use **Strategy B** is the right default.  
Add Strategy A as a `--debug` / `--slow` flag for development.

### Module layout

```
ptt/
    scraper.py          ← existing search-based scraper (keep as-is)
    index_scraper.py    ← new index-based scraper
    output/
```

### `index_scraper.py` public API

```python
def get_max_index(board: str) -> int:
    """Return current highest index number for a board."""

def fetch_index_page(client, board: str, n: int) -> list[PostMeta]:
    """Return list of PostMeta(title, url, date, author) for index page N."""

def crawl(
    board:   str,
    keyword: str,
    *,
    pages:   int  = 200,    # how many index pages back to scan
    since:   str  = "",     # ISO date floor, e.g. "2024-01-01"
    workers: int  = 8,      # parallel post-fetchers (Strategy B)
    mode:    str  = "two-phase",  # "sequential" | "two-phase" | "pipeline"
) -> list[dict]:
    """Main entry point. Returns same schema as search() in scraper.py."""

def save_csv(posts: list[dict], label: str) -> Path:
    """Write results to ptt/output/{label}_{timestamp}.csv."""
```

### CLI usage (mirrors existing scraper)

```bash
# scan last 500 index pages of Gossiping for 蝦皮
uv run python ptt/index_scraper.py 蝦皮 Gossiping 500

# with date floor
uv run python ptt/index_scraper.py 蝦皮 Gossiping 500 --since 2024-01-01

# debug mode (sequential)
uv run python ptt/index_scraper.py 蝦皮 Gossiping 10 --mode sequential
```

---

## Practical notes for PTT

- **Rate limiting:** PTT is tolerant but add a small delay (`time.sleep(0.1)`) in the
  producer to avoid hammering. The `httpx.Client` connection pool handles bursts.
- **Date early-exit:** index pages list dates; once all 20 posts on a page are older
  than `since`, stop crawling — no need to scan the full archive.
- **Deleted posts:** index pages sometimes show `(本文已被刪除)` — skip entries with no `<a>` tag.
- **Content fetching is optional:** for keyword-in-title use cases, skip phase 2 entirely
  and just return the index metadata. Much faster, no post content.
- **Dedup with search results:** URL is the stable key — combine index results with
  existing search results using `seen_urls: set[str]`.
