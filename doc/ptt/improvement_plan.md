# PTT Scraper — Improvement Plan

## Why the result count is capped

`ptt.cc/bbs/{board}/search?q={keyword}` exposes a **finite search index**, not the full post archive.
Running `uv run python ptt/scraper.py 蝦皮 Gossiping 100 30000` only returned **614 posts** because
that is everything PTT's index holds for "蝦皮" in Gossiping (posts from 2019-08-25 to 2026-05-04).
The scraper is working correctly — it exhausted all available pages and stopped when PTT showed
no more "上頁" (previous page) button.

---

## Improvement 1 — Search across multiple boards

PTT has several boards where 蝦皮-related discussion appears. Searching them in parallel multiplies coverage.

**Target boards**

| board       | focus                              |
|-------------|------------------------------------|
| Gossiping   | general chatter (current)          |
| e-shopping  | online shopping discussion         |
| e-seller    | seller / vendor discussion         |
| Stock       | market / business news             |
| Lifeismoney | deals and coupons                  |

**Approach**

```python
BOARDS = ["Gossiping", "e-shopping", "e-seller", "Stock", "Lifeismoney"]

all_posts = []
seen_urls = set()
for board in BOARDS:
    for post in search(keyword, board, pages=100):
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            all_posts.append(post)
```

Deduplication by URL prevents cross-board reposts from being counted twice.

---

## Improvement 2 — Search with multiple keyword variants

A single keyword misses related terms. Running several variants and deduplicating by URL
captures a wider slice of discussion.

**Keyword ideas for 蝦皮**

| keyword      | what it catches                        |
|--------------|----------------------------------------|
| 蝦皮         | brand name (current)                   |
| Shopee       | English / mixed-language posts         |
| 蝦皮購物     | "Shopee shopping"                      |
| 蝦皮賣家     | seller perspective                     |
| 蝦皮客服     | customer-service complaints            |
| 蝦皮物流     | logistics / delivery discussion        |

**Approach**

```python
KEYWORDS = ["蝦皮", "Shopee", "蝦皮購物", "蝦皮賣家", "蝦皮物流"]

all_posts = []
seen_urls = set()
for kw in KEYWORDS:
    for post in search(kw, board="Gossiping", pages=100):
        if post["url"] not in seen_urls:
            seen_urls.add(post["url"])
            all_posts.append(post)
```

---

## Improvement 3 — Combine boards × keywords

Run the full matrix (boards × keywords) for maximum coverage, always deduplicating by URL.

**Expected yield estimate**

| scope                        | rough post count |
|------------------------------|-----------------|
| 1 keyword × 1 board (now)    | ~600            |
| 6 keywords × 1 board         | ~2,000–3,000    |
| 1 keyword × 5 boards         | ~2,000–3,000    |
| 6 keywords × 5 boards        | ~5,000–8,000    |

Counts are estimates; actual yield depends on PTT's index depth per board.

---

## Suggested next steps

1. Add a `boards` parameter (list) to `search()` so callers can pass multiple boards in one call.
2. Add a `keywords` parameter (list) with built-in deduplication.
3. Save the combined result to a single CSV named `{primary_keyword}_{timestamp}_combined.csv`.
