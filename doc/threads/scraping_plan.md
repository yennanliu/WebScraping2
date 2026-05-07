# Threads Scraping Plan

## Goal

Scrape Threads posts by search keyword (e.g. `蝦皮`), collecting all posts from the search results page. One-shot operation.

---

## Entry Point

```
https://www.threads.net/search?q=蝦皮&serp_type=default
```

Threads search is fully JS-rendered — a plain HTTP request returns a skeleton HTML with no posts. Playwright is required.

---

## Strategy: Playwright + Network Interception

Two sub-strategies, ordered by preference:

### A. Intercept GraphQL responses (preferred)

- Threads loads search results by calling an internal GraphQL endpoint (`/api/graphql`) as you scroll
- Playwright's `page.on("response", ...)` captures these — each response is clean JSON with post arrays
- No HTML parsing needed; structured fields (text, author, timestamp, like count, post ID) come directly from the response
- Risk: Meta can change the response schema; field names may need remapping

### B. DOM scraping (fallback)

- If GraphQL responses are opaque/encrypted, scrape text directly from the rendered DOM
- Slower and more fragile (CSS selectors break on redesigns), but always accessible for public pages

---

## Scroll + Termination Logic

Threads search uses infinite scroll:

1. After page load, collect initial batch from intercepted responses
2. Scroll to bottom in a loop, wait for new network activity
3. Stop when:
   - A response returns an empty `edges` array, or
   - N consecutive scrolls produce no new posts

---

## Output Fields (per post)

| Field | Source |
|---|---|
| `post_id` | GraphQL response |
| `author` | GraphQL response |
| `text` | GraphQL response |
| `created_at` | GraphQL response (Unix timestamp → ISO) |
| `like_count` | GraphQL response |
| `reply_count` | GraphQL response |
| `url` | constructed from `post_id` |

---

## File Layout (following repo pattern)

```
threads/
    __init__.py
    scraper.py          ← Playwright logic, exposes search(keyword) → list[dict]
```

Output: `threads/output/<keyword>_<timestamp>.json`

---

## Key Unknowns (require live inspection)

1. Exact GraphQL endpoint URL and which JSON field contains the post array — open DevTools on `threads.net/search`, check Network tab
2. Whether Threads blocks headless Playwright — may need `playwright-stealth` or non-headless mode
3. Whether any cookie/header is required to return results even without login

---

## Implementation Steps

1. Write a probe script: launch Playwright, log all network responses from the search page, identify the right endpoint and payload structure
2. Build `threads/scraper.py` with scroll loop + response interception
3. Parse and normalize post fields into the output schema above
4. Save to `threads/output/<keyword>_<timestamp>.json`
