# Google Search Multi-Agent Scraper — Implementation Plan

## Goal

Build a multi-agent system that accepts a keyword, queries Google via SerpAPI, extracts structured results, and writes a clean JSON + markdown report — all orchestrated by CrewAI agents.

---

## Project Layout

Standalone sub-project inside `google_search/`, mirroring the POC app pattern:

```
google_search/
├── pyproject.toml       ← isolated deps (crewai, serpapi, openai, etc.)
├── .env                 ← API keys (gitignored)
├── .env.example         ← template committed to repo
├── .python-version      ← 3.12
├── __init__.py
├── tools.py             ← SerpAPI search tool (@tool decorator)
├── agents.py            ← agent definitions
├── tasks.py             ← task definitions
├── scraper.py           ← crew assembly + __main__ entry point
├── output/              ← saved JSON + markdown results
└── doc/
    └── plan.md          ← this file
```

---

## Dependencies (`pyproject.toml`)

```
crewai >= 0.80.0
crewai-tools >= 0.17.0
google-search-results     ← official serpapi Python client
python-dotenv >= 1.0.0
openai >= 1.0.0
```

---

## Agents (3 agents, sequential pipeline)

### 1. Search Agent
- **Role:** Google Search Specialist
- **Goal:** Fetch raw Google search results for the given keyword via SerpAPI
- **Tools:** `google_search_tool`
- **LLM:** `openai/gpt-4o-mini`

### 2. Extractor Agent
- **Role:** Data Extractor
- **Goal:** Parse the raw SerpAPI JSON and produce a clean list of structured records (title, URL, snippet, position)
- **Tools:** none (works on text passed via task context)
- **LLM:** `openai/gpt-4o-mini`

### 3. Summarizer Agent
- **Role:** Research Summarizer
- **Goal:** Write a concise markdown summary of the search results and save output files
- **Tools:** `save_results_tool`
- **LLM:** `openai/gpt-4o-mini`

---

## Tasks (sequential)

| # | Task | Agent | Input | Output |
|---|------|-------|-------|--------|
| 1 | `search_task` | Search Agent | keyword (str) | Raw SerpAPI JSON string |
| 2 | `extract_task` | Extractor Agent | context: task 1 | JSON list of `{title, url, snippet, position}` |
| 3 | `summarize_task` | Summarizer Agent | context: task 2 | Saves `output/<keyword>_<ts>.json` + `output/<keyword>_<ts>.md` |

---

## Tools (`tools.py`)

### `google_search_tool`
Wraps SerpAPI. Takes `keyword: str`, calls `GoogleSearch` with `SERPAPI_API_KEY` from env, returns the raw results JSON string.

```python
@tool("Google Search")
def google_search_tool(keyword: str) -> str:
    """Search Google for the keyword and return raw results JSON."""
```

### `save_results_tool`
Takes structured content string, writes two files to `output/`:
- `<keyword>_<timestamp>.json`
- `<keyword>_<timestamp>.md`

```python
@tool("Save Results")
def save_results_tool(content: str) -> str:
    """Save the search results summary to output files. Returns saved paths."""
```

---

## Environment Variables (`.env`)

```
OPENAI_API_KEY=sk-...
SERPAPI_API_KEY=...
```

---

## Entry Point (`scraper.py`)

```
uv run python google_search/scraper.py <keyword>
# e.g. uv run python google_search/scraper.py "python web scraping"
```

Prints the markdown summary to stdout and saves files to `output/`.

---

## Crew Assembly (`scraper.py → build_crew`)

```
Crew(
    agents=[search_agent, extractor_agent, summarizer_agent],
    tasks=[search_task, extract_task, summarize_task],
    process=Process.sequential,
    verbose=True,
)
```

---

## What is NOT included (keeping it simple)

- No async
- No retry logic
- No pagination (single SerpAPI page, ~10 results)
- No tests initially
- No hierarchical process — sequential is sufficient for this pipeline
