import json
import os
from datetime import datetime

from crewai.tools import tool
from serpapi import GoogleSearch


@tool("Google Search")
def google_search_tool(keyword: str, num_results: int = 10) -> str:
    """Search Google for the keyword. Returns a JSON array of {url, original_abstract} records.
    Paginates via SerpAPI's next-page link until num_results are collected or no more pages exist.
    Google typically exposes up to ~100 organic results per query."""
    collected = []
    start = 0

    while len(collected) < num_results:
        params = {
            "q": keyword,
            "api_key": os.environ["SERPAPI_API_KEY"],
            "num": 10,
            "start": start,
        }
        data = GoogleSearch(params).get_dict()
        organic = data.get("organic_results", [])
        if not organic:
            break
        for item in organic:
            collected.append({
                "url": item.get("link", ""),
                "original_abstract": item.get("snippet", ""),
            })
        start += len(organic)
        # stop only when SerpAPI says there is no next page
        if not data.get("serpapi_pagination", {}).get("next"):
            break

    return json.dumps(collected[:num_results], ensure_ascii=False)


@tool("Save Results")
def save_results_tool(keyword: str, json_content: str) -> str:
    """Save search results to output/<keyword>_<timestamp>.json.
    Stamps each record with created_time. Returns the saved file path."""
    os.makedirs("output", exist_ok=True)
    ts = datetime.now()
    created_time = ts.isoformat()
    slug = keyword.replace(" ", "_")
    json_path = f"output/{slug}_{ts.strftime('%Y%m%d_%H%M%S')}.json"

    records = json.loads(json_content)
    for record in records:
        record["created_time"] = created_time

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    return f"Saved {len(records)} records to {json_path}"
