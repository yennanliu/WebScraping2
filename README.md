# WebScraping2

Modular web scrapers — one directory per target site, managed with [uv](https://docs.astral.sh/uv/).

## Setup

```bash
uv sync          # creates .venv and installs all dependencies
```

## Scrapers

### PTT (`ptt/`)

Searches a PTT board by keyword, fetches the full content of each matching post, and saves results to CSV.

**Usage**

```bash
uv run python ptt/scraper.py <keyword> [board] [pages]

uv run python ptt/scraper.py 蝦皮
uv run python ptt/scraper.py iphone Gossiping 3
```

Output is saved to `ptt/output/<keyword>_<timestamp>.csv`:

| column  | description              |
|---------|--------------------------|
| title   | post title               |
| url     | full URL to the post     |
| content | body text (ads stripped) |
| time    | post timestamp from PTT  |
| author  | PTT username             |

## Architecture

Each scraper lives in its own directory and follows the same pattern:

```
<site>/
    scraper.py      # importable module + runnable __main__ block
    output/         # CSV results (gitignored)
```

`scraper.py` exposes functions that can be imported by other scripts and also runs standalone as a CLI tool that writes JSON or CSV to stdout/disk.

## Adding a new scraper

```bash
mkdir <site> && touch <site>/__init__.py
# create <site>/scraper.py following the ptt/ pattern
```

Add any site-specific dependencies to `pyproject.toml`, then `uv sync`.

## Ref
- [web_scraping — legacy project](https://github.com/yennanliu/web_scraping)
