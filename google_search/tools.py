import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from crewai.tools import tool
from openai import OpenAI
from serpapi import GoogleSearch


@tool("Google Search")
def google_search_tool(keyword: str, num_results: int = 10) -> str:
    """Search Google for keyword, paginate until num_results collected.
    original_abstract = title + snippet for richer context.
    Saves raw records to a temp file and returns the file path."""
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
            title = item.get("title", "").strip()
            snippet = item.get("snippet", "").strip()
            original_abstract = f"{title} — {snippet}" if title and snippet else (title or snippet)
            collected.append({
                "url": item.get("link", ""),
                "original_abstract": original_abstract,
            })
        start += len(organic)
        if not data.get("serpapi_pagination", {}).get("next"):
            break

    os.makedirs("output", exist_ok=True)
    slug = keyword.replace(" ", "_").replace(":", "-")
    tmp_path = f"output/.tmp_{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(collected[:num_results], f, ensure_ascii=False)

    return tmp_path


@tool("Clean Results")
def clean_results_tool(tmp_file_path: str) -> str:
    """Clean raw scraped records in parallel:
    - Regex pass: strip repeated symbols (===, ---, ***), leading ellipsis, excess whitespace
    - LLM pass: remove navigation text, cookie notices, and other filler
    Saves cleaned records and returns the new file path."""
    with open(tmp_file_path, encoding="utf-8") as f:
        records = json.load(f)

    client = OpenAI()

    def clean(record):
        text = record.get("original_abstract", "")
        # regex: structural noise
        text = re.sub(r'[=\-_*#|]{3,}', ' ', text)
        text = re.sub(r'^[\s.…。\-]+', '', text)
        text = re.sub(r'\s+', ' ', text).strip()

        if text:
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{
                    "role": "user",
                    "content": (
                        "Clean this raw webpage snippet. "
                        "Remove: navigation links, cookie/privacy notices, \"Click here\", "
                        "\"Read more\", repeated symbols, and any other filler content. "
                        "Keep only text that meaningfully describes what the page is about. "
                        "Return the cleaned text only, no explanation:\n\n" + text
                    ),
                }],
                max_tokens=150,
            )
            text = resp.choices[0].message.content.strip()

        record["original_abstract"] = text
        return record

    cleaned = [None] * len(records)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(clean, rec): i for i, rec in enumerate(records)}
        for future in as_completed(futures):
            cleaned[futures[future]] = future.result()

    cleaned_path = tmp_file_path.replace(".tmp_", ".cleaned_")
    with open(cleaned_path, "w", encoding="utf-8") as f:
        json.dump(cleaned, f, ensure_ascii=False)

    # remove the raw tmp file now that cleaning is done
    try:
        os.remove(tmp_file_path)
    except FileNotFoundError:
        pass

    return cleaned_path


@tool("Enrich Results")
def enrich_results_tool(cleaned_file_path: str) -> str:
    """Read cleaned records, generate ai_summary in Traditional Chinese for each record
    in parallel using OpenAI. Saves enriched records and returns the new file path."""
    with open(cleaned_file_path, encoding="utf-8") as f:
        records = json.load(f)

    client = OpenAI()

    def summarize(record):
        abstract = record.get("original_abstract", "").strip()
        if not abstract:
            record["ai_summary"] = ""
            return record
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{
                "role": "user",
                "content": f"請用一句繁體中文描述以下網頁的主題：\n{abstract}",
            }],
            max_tokens=100,
        )
        record["ai_summary"] = resp.choices[0].message.content.strip()
        return record

    enriched = [None] * len(records)
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(summarize, rec): i for i, rec in enumerate(records)}
        for future in as_completed(futures):
            enriched[futures[future]] = future.result()

    enriched_path = cleaned_file_path.replace(".cleaned_", ".enriched_")
    with open(enriched_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False)

    try:
        os.remove(cleaned_file_path)
    except FileNotFoundError:
        pass

    return enriched_path


@tool("Save Results")
def save_results_tool(keyword: str, enriched_file_path: str) -> str:
    """Read enriched records, stamp created_time on each, write final output file,
    clean up temp file, and return the saved path."""
    with open(enriched_file_path, encoding="utf-8") as f:
        records = json.load(f)

    created_time = datetime.now().isoformat()
    for record in records:
        record["created_time"] = created_time

    slug = keyword.replace(" ", "_").replace(":", "-")
    json_path = f"output/{slug}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    try:
        os.remove(enriched_file_path)
    except FileNotFoundError:
        pass

    return f"Saved {len(records)} records to {json_path}"
