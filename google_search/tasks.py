from crewai import Agent, Task


def search_task(agent: Agent, keyword: str, num_results: int) -> Task:
    return Task(
        description=(
            f'Use the Google Search tool to search for: "{keyword}". '
            f"Collect {num_results} results (pass num_results={num_results} to the tool). "
            "Return the full raw JSON string."
        ),
        expected_output=f"A raw JSON string containing up to {num_results} organic search result objects from SerpAPI.",
        agent=agent,
    )


def extract_task(agent: Agent, prior: Task) -> Task:
    return Task(
        description=(
            "The previous task produced a JSON array of records, each with 'url' and 'original_abstract'.\n"
            "Your job: add an 'ai_summary' field to EVERY record — a one-sentence summary of what that page is about.\n"
            "IMPORTANT: preserve every record as-is. Do not filter, merge, or drop any records.\n"
            "Return a valid JSON array containing ALL records with the added 'ai_summary' field."
        ),
        expected_output=(
            'The complete JSON array with ai_summary added to each record: '
            '[{"url": "...", "original_abstract": "...", "ai_summary": "..."}, ...]'
        ),
        agent=agent,
        context=[prior],
    )


def save_task(agent: Agent, keyword: str, prior: Task) -> Task:
    return Task(
        description=(
            f'The keyword was: "{keyword}". '
            "Call the Save Results tool with the keyword and the full JSON array string from the previous task."
        ),
        expected_output="Confirmation message with the file path that was saved.",
        agent=agent,
        context=[prior],
    )
