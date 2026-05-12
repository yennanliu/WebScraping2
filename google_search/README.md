# Google Search Multi-Agent Scraper

A multi-agent system that queries Google by keyword, extracts structured results, and writes a clean JSON + markdown report — orchestrated by [CrewAI](https://crewai.com/).

---

## Architecture

Three agents run in a sequential pipeline:

```
keyword + count
  │
  ▼
[Search Agent] ──── SerpAPI (paginated) ────► raw JSON results
  │
  ▼
[Extractor Agent] ──────────────────────────► [{url, original_abstract, ai_summary}, ...]
  │
  ▼
[Persister Agent] ──────────────────────────► output/<keyword>_<ts>.json
                                               (created_time stamped per record)
```

| Agent | Role | Tool |
|---|---|---|
| Search Agent | Queries Google via SerpAPI, paginates to hit target count | `google_search_tool` |
| Extractor Agent | Parses raw JSON, generates AI summary per result | — |
| Persister Agent | Stamps `created_time` and saves final JSON | `save_results_tool` |

---

## Key Features

- **Multi-agent separation of concerns** — each agent owns one step; easy to swap or extend individually
- **CrewAI sequential process** — tasks pass context automatically, no manual wiring between agents
- **Paginated SerpAPI** — fetches up to 100 results per API call, loops until the target count is reached
- **AI summary per result** — Extractor Agent writes a one-sentence `ai_summary` alongside the raw `original_abstract`
- **Structured JSON output** — every record has `url`, `original_abstract`, `ai_summary`, `created_time`
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
# default 10 results
uv run python scraper.py "python web scraping 2025"

# specify record count
uv run python scraper.py "蝦皮" 500
```

Results are saved to `output/`:
```
output/蝦皮_20260512_153000.json
```

Each record in the JSON looks like:
```json
{
  "url": "https://shopee.tw/...",
  "original_abstract": "Raw snippet text from Google search result...",
  "ai_summary": "Shopee is a leading e-commerce platform in Taiwan offering...",
  "created_time": "2026-05-12T15:30:00.123456"
}
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
