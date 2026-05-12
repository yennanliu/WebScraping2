import json
import os
from datetime import datetime

from crewai.tools import tool
from serpapi import GoogleSearch


@tool("Google Search")
def google_search_tool(keyword: str) -> str:
    """Search Google for the keyword and return raw results as a JSON string."""
    params = {
        "q": keyword,
        "api_key": os.environ["SERPAPI_API_KEY"],
        "num": 10,
    }
    results = GoogleSearch(params).get_dict()
    organic = results.get("organic_results", [])
    return json.dumps(organic, ensure_ascii=False)


@tool("Save Results")
def save_results_tool(keyword: str, json_content: str, markdown_content: str) -> str:
    """Save search results to output/<keyword>_<timestamp>.json and .md. Returns saved paths."""
    os.makedirs("output", exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = keyword.replace(" ", "_")
    json_path = f"output/{slug}_{ts}.json"
    md_path = f"output/{slug}_{ts}.md"
    with open(json_path, "w", encoding="utf-8") as f:
        f.write(json_content)
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(markdown_content)
    return f"Saved: {json_path}, {md_path}"
