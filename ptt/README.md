# PTT Scraper

Scrape posts from [ptt.cc](https://www.ptt.cc) by keyword. Two scrapers — pick based on how much history you need.

---

## Scrapers

### `scraper.py` — Search-based

Uses PTT's built-in search endpoint. Fast but capped at ~600–800 results per keyword (PTT's index limit).

```bash
uv run python ptt/scraper.py <keyword> [board] [pages] [count]
```

| arg | default | description |
|-----|---------|-------------|
| keyword | — | search term, e.g. `蝦皮` |
| board | `Gossiping` | PTT board name |
| pages | `1` | search result pages to walk |
| count | `0` | max records (0 = unlimited) |

```bash
uv run python ptt/scraper.py 蝦皮 Gossiping 30
```

---

### `index_scraper.py` — Index-based (recommended for history)

Crawls `index{N}.html` pages directly. Bypasses the search cap — covers the full board archive.

```bash
uv run python ptt/index_scraper.py <keyword> [board] [pages] [workers]
```

| arg | default | description |
|-----|---------|-------------|
| keyword | — | title match term, e.g. `蝦皮` |
| board | `Gossiping` | PTT board name |
| pages | `200` | how many index pages back to scan (20 posts/page) |
| workers | `8` | parallel threads for post fetching |

```bash
# ~3 months of Gossiping (≈ 5000 pages)
uv run python ptt/index_scraper.py 蝦皮 Gossiping 5000

# resume an interrupted run — same command, picks up automatically
uv run python ptt/index_scraper.py 蝦皮 Gossiping 5000
```

**Coverage guide for Gossiping** (~55 new pages/day):

| pages | time covered |
|-------|-------------|
| 500 | ~9 days |
| 5,000 | ~3 months |
| 20,000 | ~1 year |
| 50,000 | full archive |

Output is saved to `ptt/output/<keyword>_<board>_<timestamp>.csv`.

---

## Main Features

- **TLS fingerprint bypass** — uses `curl_cffi` with `impersonate="chrome131"` to pass PTT's browser check
- **Resume support** (`index_scraper` only) — progress saved after every index page; re-run the same command to continue
- **Parallel post fetching** (`index_scraper` only) — `ThreadPoolExecutor` with thread-local sessions
- **Content cleaning** — strips PTT signatures, metadata lines, decorative separators, URLs, and app banners (`Sent from JPTT…`) before saving

---

## Architecture

```
ptt/
├── scraper.py          search-based scraper  →  fetch_post(), search(), save_csv()
├── index_scraper.py    index-based scraper   →  crawl(), get_max_index()
├── clean.py            shared cleaning       →  clean_content()
├── script/
│   └── clean_data.py   post-process existing CSVs (uses clean.py)
└── output/
    ├── *.csv           scraping results
    └── .*.json         resume progress files (hidden, auto-managed)
```

`index_scraper.py` runs in two phases:

```
Phase 1 (serial)    index[N] → index[N-1] → …  collect matched post URLs
Phase 2 (parallel)  ThreadPoolExecutor fetches all matched post URLs → CSV
```

Progress is written to `output/.{board}_{keyword}_progress.json` after every request in both phases.

---

## Output Schema

| column | description |
|--------|-------------|
| `title` | post title |
| `url` | canonical post URL |
| `create_time` | ISO-8601 timestamp |
| `author` | PTT username |
| `content` | cleaned post body |
