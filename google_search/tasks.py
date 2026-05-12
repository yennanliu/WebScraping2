from crewai import Agent, Task


def search_task(agent: Agent, keyword: str, num_results: int) -> Task:
    return Task(
        description=(
            f'Use the Google Search tool to search for: "{keyword}". '
            f"Collect {num_results} results (pass num_results={num_results} to the tool). "
            "Return the full raw JSON string."
        ),
        expected_output=f"A raw JSON string containing up to {num_results} organic search result objects.",
        agent=agent,
    )


def enrich_task(agent: Agent, prior: Task) -> Task:
    return Task(
        description=(
            "Call the Enrich Results tool, passing the entire JSON string from the previous task as 'records_json'. "
            "Return the enriched JSON string exactly as the tool returns it."
        ),
        expected_output='A JSON array where every record has url, original_abstract, and ai_summary fields.',
        agent=agent,
        context=[prior],
    )


def save_task(agent: Agent, keyword: str, prior: Task) -> Task:
    return Task(
        description=(
            f'The keyword was: "{keyword}". '
            "Call the Save Results tool with the keyword and the full JSON string from the previous task."
        ),
        expected_output="Confirmation message with the file path that was saved.",
        agent=agent,
        context=[prior],
    )
