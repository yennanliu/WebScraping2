# Google Search Multi-Agent Scraper

A multi-agent system that queries Google by keyword, extracts structured results, and writes a clean JSON + markdown report — orchestrated by [CrewAI](https://crewai.com/).

---

## Architecture

Three agents run in a sequential pipeline:

```
keyword
  │
  ▼
[Search Agent] ──── SerpAPI ────► raw JSON results
  │
  ▼
[Extractor Agent] ──────────────► clean list: {position, title, url, snippet}
  │
  ▼
[Summarizer Agent] ─────────────► output/<keyword>_<ts>.json
                                   output/<keyword>_<ts>.md
```

| Agent | Role | Tool |
|---|---|---|
| Search Agent | Queries Google via SerpAPI | `google_search_tool` |
| Extractor Agent | Parses raw JSON into structured records | — |
| Summarizer Agent | Writes summary and persists files | `save_results_tool` |

---

## Key Features

- **Multi-agent separation of concerns** — each agent owns one step; easy to swap or extend individually
- **CrewAI sequential process** — tasks pass context automatically, no manual wiring between agents
- **SerpAPI integration** — reliable Google results without browser automation
- **Dual output** — JSON for downstream processing, markdown for human readability
- **Isolated environment** — own `pyproject.toml` + `.venv`, no dependency conflicts with the parent repo

---

## How to Run

**1. Install dependencies**
```bash
cd google_search
uv sync
```

**2. Set up API keys**
```bash
cp .env.example .env
# edit .env and fill in:
# OPENAI_API_KEY=sk-...
# SERPAPI_API_KEY=...
```

**3. Run**
```bash
uv run python scraper.py "your keyword"
# e.g.
uv run python scraper.py "python web scraping 2025"
```

Results are saved to `output/`:
```
output/python_web_scraping_2025_20260512_153000.json
output/python_web_scraping_2025_20260512_153000.md
```

---

## File Structure

```
google_search/
├── scraper.py        ← entry point: crew assembly + __main__
├── agents.py         ← agent definitions (search, extractor, summarizer)
├── tasks.py          ← task definitions (search, extract, summarize)
├── tools.py          ← SerpAPI search tool + file save tool
├── pyproject.toml    ← project deps (crewai, serpapi, openai)
├── .env.example      ← API key template
├── output/           ← generated JSON + markdown reports
└── doc/
    └── plan.md       ← implementation plan
```
