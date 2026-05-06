# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync                        # install all deps (including dev)
uv run python ptt/scraper.py   # run a scraper directly
uv run python ptt/scraper.py Gossiping 2  # board, pages

uv run pytest                  # run all tests
uv run pytest ptt/             # run tests for one scraper

uv run ruff check .            # lint
uv run ruff format .           # format
```

## Architecture

Each target site lives in its own top-level directory. The pattern is:

```
<site>/
    __init__.py
    scraper.py      ← all logic for that site
    test_scraper.py ← tests (when added)
```

`scraper.py` is both importable (exposes functions) and runnable as a script (`__main__` block prints JSON to stdout). No shared utilities layer — keep each scraper self-contained.

**Current scrapers**

| Dir  | Target              | Entry point    |
|------|---------------------|----------------|
| ptt/ | ptt.cc bulletin board | `fetch_board(board, pages)` |

**Stack:** `httpx` for HTTP, `beautifulsoup4` + `lxml` for parsing. No async by default — add it per-scraper if throughput requires it.

## Adding a new scraper

1. `mkdir <site> && touch <site>/__init__.py`
2. Create `<site>/scraper.py` following the `ptt/` pattern
3. No changes to root `pyproject.toml` needed unless the site requires extra dependencies
