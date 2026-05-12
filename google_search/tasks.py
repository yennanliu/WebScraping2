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
            "Parse the raw SerpAPI JSON from the previous task. "
            "For each result produce a record with exactly these fields:\n"
            "- url: the result link\n"
            "- original_abstract: the raw snippet text from Google\n"
            "- ai_summary: a one-sentence summary of what the page is about\n\n"
            "Return a valid JSON array of these records and nothing else."
        ),
        expected_output=(
            'A JSON array, e.g. [{"url": "https://...", "original_abstract": "...", "ai_summary": "..."}, ...]'
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
