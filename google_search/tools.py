import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from crewai.tools import tool
from openai import OpenAI
from serpapi import GoogleSearch


@tool("Google Search")
def google_search_tool(keyword: str, num_results: int = 10) -> str:
    """Search Google for keyword, paginate until num_results collected.
    Saves raw records to a temp file and returns the file path (not the JSON)."""
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
        if not data.get("serpapi_pagination", {}).get("next"):
            break

    os.makedirs("output", exist_ok=True)
    slug = keyword.replace(" ", "_")
    tmp_path = f"output/.tmp_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(collected[:num_results], f, ensure_ascii=False)

    return tmp_path


@tool("Enrich Results")
def enrich_results_tool(tmp_file_path: str) -> str:
    """Read raw records from tmp_file_path, add ai_summary to each record in parallel,
    save enriched records to a new temp file, and return that file path."""
    with open(tmp_file_path, encoding="utf-8") as f:
        records = json.load(f)

    client = OpenAI()

    def summarize(record):
        abstract = record.get("original_abstract", "").strip()
        if not abstract:
            record["ai_summary"] = ""
            return record
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": f"In one sentence, summarize what this webpage is about:\n{abstract}"}],
            max_tokens=80,
        )
        record["ai_summary"] = resp.choices[0].message.content.strip()
        return record

    enriched = [None] * len(records)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(summarize, rec): i for i, rec in enumerate(records)}
        for future in as_completed(futures):
            enriched[futures[future]] = future.result()

    enriched_path = tmp_file_path.replace(".tmp_", ".enriched_")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False)

    return enriched_path


@tool("Save Results")
def save_results_tool(keyword: str, enriched_file_path: str) -> str:
    """Read enriched records from enriched_file_path, stamp created_time on each,
    write the final output file, clean up temp files, and return the saved path."""
    with open(enriched_file_path, encoding="utf-8") as f:
        records = json.load(f)

    created_time = datetime.now().isoformat()
    for record in records:
        record["created_time"] = created_time

    slug = keyword.replace(" ", "_")
    json_path = f"output/{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # clean up temp files
    for path in [enriched_file_path, enriched_file_path.replace(".enriched_", ".tmp_")]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    return f"Saved {len(records)} records to {json_path}"
